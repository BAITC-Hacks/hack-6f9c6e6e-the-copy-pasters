import pandas as pd
from fastapi import APIRouter, HTTPException, Request, Response
import threading
import time

from ..config import OPENAI_API_KEY
from ..repositories import supabase
from ..services.ai_analysis import AIAnalysisError, analyze_provider
from ..services.catalog import get_options
from ..services.matching import find_matches
from ..services.providers import csv_profile_to_dict, personal_profile_to_dict, personal_rows_to_frame
from .schemas import AIAnalysisRequest, AuthCredentials, MatchRequest, MatchResponse, OptionsResponse, PersonalProviderInput


router = APIRouter(prefix="/api")
_AI_REQUESTS: dict[str, list[float]] = {}
_AI_REQUESTS_LOCK = threading.Lock()


def _bearer(request: Request, *, required: bool = False) -> str | None:
    value = request.headers.get("authorization", "")
    if not value:
        if required:
            raise HTTPException(status_code=401, detail="Войдите в аккаунт, чтобы продолжить.")
        return None
    scheme, _, token = value.partition(" ")
    if scheme.casefold() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Сессия недействительна. Войдите снова.")
    return token.strip()


def _supabase_error(error: supabase.SupabaseError, *, signup: bool = False):
    if error.status == 401:
        raise HTTPException(status_code=401, detail="Проверьте email и пароль или войдите снова.") from None
    if signup and error.status in {400, 422}:
        raise HTTPException(status_code=400, detail="Не удалось создать аккаунт. Проверьте email и пароль.") from None
    if error.status == 404:
        raise HTTPException(status_code=404, detail="Профиль не найден или у вас нет к нему доступа.") from None
    if error.status in {400, 409, 422}:
        raise HTTPException(status_code=400, detail="Проверьте поля профиля и настройки таблицы Supabase.") from None
    raise HTTPException(status_code=503, detail="Supabase недоступен. Проверьте настройки и SQL-миграцию.") from None


def _current_user(token: str) -> dict:
    try:
        user = supabase.get_user(token)
    except supabase.SupabaseError as error:
        _supabase_error(error)
    if not isinstance(user, dict) or not user.get("id"):
        raise HTTPException(status_code=401, detail="Сессия недействительна. Войдите снова.")
    return user


def _catalog_with_personal(request: Request, token: str | None) -> pd.DataFrame:
    catalog = request.app.state.catalog
    if not token:
        return catalog
    try:
        _current_user(token)
    except HTTPException as error:
        if error.status_code == 503:
            return catalog
        raise
    try:
        rows = supabase.list_personal(token)
    except supabase.SupabaseError as error:
        if error.status == 503:
            return catalog
        _supabase_error(error)
    personal = personal_rows_to_frame(rows)
    return pd.concat([catalog, personal], ignore_index=True) if not personal.empty else catalog


def _profile_for_id(request: Request, provider_id: str, token: str | None) -> dict:
    if provider_id.startswith("personal:"):
        token = token or _bearer(request, required=True)
        _current_user(token)
        try:
            rows = supabase.list_personal(token)
        except supabase.SupabaseError as error:
            _supabase_error(error)
        row_id = provider_id.removeprefix("personal:")
        row = next((item for item in rows if str(item.get("id")) == row_id), None)
        if not row:
            raise HTTPException(status_code=404, detail="Профиль не найден или у вас нет к нему доступа.")
        return personal_profile_to_dict(row)
    rows = request.app.state.catalog
    found = rows[rows["id"].astype(str).eq(provider_id)]
    if found.empty:
        raise HTTPException(status_code=404, detail="Подрядчик не найден.")
    return csv_profile_to_dict(next(found.itertuples(index=False)))


def _limit_ai_requests(request: Request, token: str | None) -> None:
    if token:
        user = _current_user(token)
        bucket = f"user:{user['id']}"
    else:
        bucket = f"ip:{request.client.host if request.client else 'unknown'}"
    now = time.monotonic()
    with _AI_REQUESTS_LOCK:
        recent = [stamp for stamp in _AI_REQUESTS.get(bucket, []) if now - stamp < 60]
        if len(recent) >= 8:
            raise HTTPException(status_code=429, detail="Лимит ИИ-запросов достигнут. Подождите минуту и попробуйте снова.")
        recent.append(now)
        _AI_REQUESTS[bucket] = recent


@router.get("/config")
def public_config():
    return {"accounts_enabled": supabase.is_configured(), "ai_enabled": bool(OPENAI_API_KEY)}


@router.post("/auth/signup")
def signup(request: Request, credentials: AuthCredentials):
    if not supabase.is_configured():
        raise HTTPException(status_code=503, detail="Сначала настройте Supabase в локальном .env.")
    try:
        result = supabase.sign_up(credentials.email, credentials.password, str(request.base_url))
    except supabase.SupabaseError as error:
        _supabase_error(error, signup=True)
    session = (result.get("session") or result) if isinstance(result, dict) else None
    if session and session.get("access_token"):
        return {
            "access_token": session["access_token"],
            "refresh_token": session.get("refresh_token"),
            "user": result.get("user") or {},
            "confirmation_required": False,
        }
    return {"confirmation_required": True, "email": credentials.email}


@router.post("/auth/login")
def login(credentials: AuthCredentials):
    if not supabase.is_configured():
        raise HTTPException(status_code=503, detail="Сначала настройте Supabase в локальном .env.")
    try:
        result = supabase.sign_in(credentials.email, credentials.password)
    except supabase.SupabaseError as error:
        _supabase_error(error)
    return {"access_token": result.get("access_token"), "refresh_token": result.get("refresh_token"), "user": result.get("user") or {}}


@router.post("/auth/refresh")
def refresh_auth(body: dict):
    refresh_token = body.get("refresh_token") if isinstance(body, dict) else None
    if not isinstance(refresh_token, str) or not refresh_token:
        raise HTTPException(status_code=401, detail="Сессия завершилась. Войдите снова.")
    try:
        result = supabase.refresh_session(refresh_token)
    except supabase.SupabaseError as error:
        _supabase_error(error)
    return {"access_token": result.get("access_token"), "refresh_token": result.get("refresh_token"), "user": result.get("user") or {}}


@router.get("/auth/me")
def current_user(request: Request):
    return _current_user(_bearer(request, required=True))


@router.post("/auth/logout", status_code=204)
def logout(request: Request):
    token = _bearer(request, required=True)
    try:
        supabase.sign_out(token)
    except supabase.SupabaseError:
        # The browser drops its access token even if the upstream logout is unavailable.
        pass
    return Response(status_code=204)


@router.get("/options", response_model=OptionsResponse)
def options(request: Request, city: str | None = None):
    return get_options(_catalog_with_personal(request, _bearer(request)), city=city)


@router.post("/match", response_model=MatchResponse)
def match(request: Request, query: MatchRequest):
    catalog = _catalog_with_personal(request, _bearer(request))
    global_options = get_options(catalog)
    if query.city.casefold() not in {city.casefold() for city in global_options["cities"]}:
        raise HTTPException(status_code=422, detail={"field": "city", "message": "Выберите город из каталога."})
    if query.event_format.casefold() not in {value.casefold() for value in global_options["event_formats"]}:
        raise HTTPException(status_code=422, detail={"field": "event_format", "message": "Формат отсутствует в каталоге."})
    if query.language and query.language.casefold() not in {value.casefold() for value in global_options["languages"]}:
        raise HTTPException(status_code=422, detail={"field": "language", "message": "Язык отсутствует в каталоге."})

    return find_matches(
        catalog,
        city=query.city,
        event_date=query.event_date,
        event_format=query.event_format,
        category=query.category,
        budget_kzt=query.budget_kzt,
        language=query.language,
        hours=query.hours,
    )


@router.get("/providers/{provider_id}")
def provider_details(request: Request, provider_id: str):
    return _profile_for_id(request, provider_id, _bearer(request))


@router.get("/personal-providers")
def list_my_providers(request: Request):
    token = _bearer(request, required=True)
    _current_user(token)
    try:
        return [personal_profile_to_dict(row) for row in supabase.list_personal(token)]
    except supabase.SupabaseError as error:
        _supabase_error(error)


@router.post("/personal-providers", status_code=201)
def create_my_provider(request: Request, profile: PersonalProviderInput):
    token = _bearer(request, required=True)
    user = _current_user(token)
    try:
        row = supabase.create_personal(token, user["id"], profile.model_dump(mode="json"))
        return personal_profile_to_dict(row)
    except supabase.SupabaseError as error:
        _supabase_error(error)


@router.put("/personal-providers/{profile_id}")
def update_my_provider(request: Request, profile_id: str, profile: PersonalProviderInput):
    token = _bearer(request, required=True)
    _current_user(token)
    if not profile_id.startswith("personal:"):
        raise HTTPException(status_code=404, detail="Профиль не найден.")
    row_id = profile_id.removeprefix("personal:")
    try:
        row = supabase.update_personal(token, row_id, profile.model_dump(mode="json"))
        return personal_profile_to_dict(row)
    except supabase.SupabaseError as error:
        _supabase_error(error)


@router.delete("/personal-providers/{profile_id}", status_code=204)
def delete_my_provider(request: Request, profile_id: str):
    token = _bearer(request, required=True)
    _current_user(token)
    if not profile_id.startswith("personal:"):
        raise HTTPException(status_code=404, detail="Профиль не найден.")
    row_id = profile_id.removeprefix("personal:")
    try:
        supabase.delete_personal(token, row_id)
    except supabase.SupabaseError as error:
        _supabase_error(error)
    return Response(status_code=204)


@router.post("/providers/{provider_id}/analysis")
def provider_analysis(request: Request, provider_id: str, criteria: AIAnalysisRequest):
    token = _bearer(request)
    _limit_ai_requests(request, token)
    profile = _profile_for_id(request, provider_id, token)
    try:
        return analyze_provider(profile, criteria.model_dump(mode="json", exclude_none=True))
    except AIAnalysisError as error:
        if error.status == 429:
            raise HTTPException(status_code=429, detail="Лимит ИИ-запросов временно достигнут. Попробуйте позже.") from None
        raise HTTPException(status_code=503, detail="ИИ-анализ сейчас недоступен. Проверьте API-ключ и попробуйте позже.") from None
