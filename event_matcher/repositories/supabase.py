"""Minimal Supabase Auth and PostgREST client using per-user JWTs and RLS."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL


class SupabaseError(Exception):
    def __init__(self, status: int = 503):
        self.status = status
        super().__init__("Supabase request failed")


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY)


def _request(path: str, *, method: str = "GET", token: str | None = None,
             body: dict | None = None, prefer: str | None = None):
    if not is_configured():
        raise SupabaseError(503)
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"apikey": SUPABASE_PUBLISHABLE_KEY, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    request = Request(f"{SUPABASE_URL}/{path.lstrip('/')}", data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=12) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else None
    except HTTPError as error:
        status = error.code
        error.close()
        raise SupabaseError(status) from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise SupabaseError(503) from None


def sign_up(email: str, password: str, redirect_url: str | None = None) -> dict:
    path = "auth/v1/signup"
    if redirect_url:
        path += "?" + urlencode({"redirect_to": redirect_url})
    return _request(path, method="POST", body={"email": email, "password": password})


def sign_in(email: str, password: str) -> dict:
    return _request("auth/v1/token?grant_type=password", method="POST",
                    body={"email": email, "password": password})


def refresh_session(refresh_token: str) -> dict:
    return _request("auth/v1/token?grant_type=refresh_token", method="POST",
                    body={"refresh_token": refresh_token})


def sign_out(token: str) -> None:
    _request("auth/v1/logout", method="POST", token=token)


def get_user(token: str) -> dict:
    return _request("auth/v1/user", token=token)


def list_personal(token: str) -> list[dict]:
    try:
        rows = _request("rest/v1/personal_contractors?select=*&order=created_at.desc", token=token)
    except SupabaseError as error:
        if error.status == 404:
            raise SupabaseError(503) from None
        raise
    return rows if isinstance(rows, list) else []


def create_personal(token: str, owner_id: str, profile: dict) -> dict:
    row = {**profile, "owner_id": owner_id}
    rows = _request("rest/v1/personal_contractors?select=*", method="POST", token=token,
                    body=row, prefer="return=representation")
    if not isinstance(rows, list) or not rows:
        raise SupabaseError(502)
    return rows[0]


def update_personal(token: str, profile_id: str, profile: dict) -> dict:
    query = urlencode({"id": f"eq.{profile_id}", "select": "*"})
    rows = _request(f"rest/v1/personal_contractors?{query}", method="PATCH", token=token,
                    body=profile, prefer="return=representation")
    if not isinstance(rows, list) or not rows:
        raise SupabaseError(404)
    return rows[0]


def delete_personal(token: str, profile_id: str) -> None:
    query = urlencode({"id": f"eq.{profile_id}"})
    _request(f"rest/v1/personal_contractors?{query}", method="DELETE", token=token)
