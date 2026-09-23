"""Conversions between persisted personal profiles and the matcher catalog."""

import pandas as pd

from ..data import truthy


def personal_profile_to_dict(row: dict) -> dict:
    return {
        "id": f"personal:{row['id']}",
        "name": row.get("name", ""),
        "categories": row.get("categories") or [],
        "city": row.get("city", ""),
        "price_from_kzt": row.get("price_from_kzt"),
        "event_formats": row.get("event_formats") or [],
        "languages": row.get("languages") or [],
        "max_hours": row.get("max_hours"),
        "busy_dates": row.get("busy_dates") or [],
        "description": row.get("description") or "",
        "synthetic": False,
        "city_imputed": False,
        "price_imputed": False,
        "source": "personal",
        "phone": row.get("phone"),
        "website": row.get("website"),
        "social_link": row.get("social_link"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def csv_profile_to_dict(row) -> dict:
    return {
        "id": str(row.id),
        "name": str(row.anon_name),
        "categories": [part.strip() for part in str(row.categories).split("|") if part.strip()],
        "city": str(row.city),
        "price_from_kzt": None if pd.isna(row.price_from_kzt) else int(row.price_from_kzt),
        "event_formats": [part.strip() for part in str(row.event_formats).split("|") if part.strip()],
        "languages": [part.strip() for part in str(row.languages).split("|") if part.strip()],
        "max_hours": None if pd.isna(row.max_hours) else float(row.max_hours),
        "busy_dates": [part.strip() for part in str(row.busy_dates).split("|") if part.strip()],
        "description": str(row.description or ""),
        "synthetic": truthy(row.synthetic),
        "city_imputed": truthy(row.city_imputed),
        "price_imputed": truthy(row.price_imputed),
        "source": "catalog",
        "phone": None,
        "website": None,
        "social_link": None,
    }


def personal_rows_to_frame(rows: list[dict]) -> pd.DataFrame:
    records = []
    for row in rows:
        records.append({
            "id": f"personal:{row['id']}",
            "anon_name": row.get("name", ""),
            "categories": "|".join(row.get("categories") or []),
            "city": row.get("city", ""),
            "city_imputed": False,
            "synthetic": False,
            "price_from_kzt": row.get("price_from_kzt"),
            "price_imputed": False,
            "event_formats": "|".join(row.get("event_formats") or []),
            "languages": "|".join(row.get("languages") or []),
            "max_hours": row.get("max_hours"),
            "busy_dates": "|".join(str(value) for value in (row.get("busy_dates") or [])),
            "description": row.get("description") or "",
        })
    return pd.DataFrame(records)

