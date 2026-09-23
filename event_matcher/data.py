"""Small normalization helpers shared by repository and matching services."""

import pandas as pd


def normalized(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().casefold()


def items(value) -> list[str]:
    return [part.strip().casefold() for part in str(value or "").split("|") if part.strip()]


def truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"true", "1", "yes", "да"}
