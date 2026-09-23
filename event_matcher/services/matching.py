from datetime import date

import pandas as pd

from ..data import items, normalized, truthy
from .explanations import explain_match
from .relevance import text_relevance


def _optional_number(value):
    return None if pd.isna(value) else float(value)


def _public_match(row, explanation: str) -> dict:
    return {
        "id": str(row.id),
        "name": str(row.anon_name),
        "categories": [part.strip() for part in str(row.categories).split("|") if part.strip()],
        "city": str(row.city),
        "price_from_kzt": int(row.price_from_kzt),
        "event_formats": [part.strip() for part in str(row.event_formats).split("|") if part.strip()],
        "languages": [part.strip() for part in str(row.languages).split("|") if part.strip()],
        "max_hours": _optional_number(row.max_hours),
        "busy_dates": [part.strip() for part in str(row.busy_dates).split("|") if part.strip()],
        "synthetic": truthy(row.synthetic),
        "city_imputed": truthy(row.city_imputed),
        "price_imputed": truthy(row.price_imputed),
        "source": "personal" if str(row.id).startswith("personal:") else "catalog",
        "explanation": explanation,
    }


def find_matches(
    frame,
    *,
    city: str,
    event_date: date,
    event_format: str,
    category: str,
    budget_kzt: int,
    language: str | None = None,
    hours: int | None = None,
) -> dict:
    """Filter hard requirements then rank eligible providers deterministically."""
    city_mask = frame["city"].map(normalized).eq(normalized(city))
    category_mask = frame["categories"].apply(lambda value: normalized(category) in items(value))
    city_category = frame[city_mask & category_mask].copy()
    if city_category.empty:
        return {"status": "no_category", "candidate_count": 0, "reasons": {}, "matches": []}

    checks = {
        "busy": lambda row: event_date.isoformat() in items(row.busy_dates),
        "format": lambda row: normalized(event_format) not in items(row.event_formats),
        "budget": lambda row: pd.isna(row.price_from_kzt) or float(row.price_from_kzt) > budget_kzt,
        "language": lambda row: bool(language) and normalized(language) not in items(row.languages),
        "hours": lambda row: bool(hours) and (
            pd.isna(row.max_hours) or float(row.max_hours) < hours
        ),
    }
    reasons = {key: 0 for key in checks}
    eligible = []
    for row in city_category.itertuples(index=False):
        failed = [name for name, check in checks.items() if check(row)]
        for name in failed:
            reasons[name] += 1
        if failed:
            continue

        price = float(row.price_from_kzt)
        price_fit = 1.0 - price / max(float(budget_kzt), 1.0)
        profile_relevance = text_relevance(row.description, event_format, category)
        if hours and pd.notna(row.max_hours):
            duration_fit = 1.0 - min(float(row.max_hours) - hours, 24.0) / 24.0
            score = 0.55 * profile_relevance + 0.25 * price_fit + 0.20 * duration_fit
        else:
            score = 0.65 * profile_relevance + 0.35 * price_fit
        eligible.append((score, str(row.id), row))

    eligible.sort(key=lambda item: (-item[0], item[1]))
    matches = [
        _public_match(
            row,
            explain_match(
                row, budget_kzt, event_date, event_format, category,
                hours=hours, language=language,
            ),
        )
        for _, _, row in eligible[:3]
    ]
    return {
        "status": "matched" if matches else "filtered_out",
        "candidate_count": len(city_category),
        "reasons": reasons,
        "matches": matches,
    }
