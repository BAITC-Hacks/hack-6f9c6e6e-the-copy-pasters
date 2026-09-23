from ..data import normalized


def _values(series):
    values = set()
    for cell in series.fillna(""):
        values.update(part.strip() for part in str(cell).split("|") if part.strip())
    return sorted(values, key=str.casefold)


def get_options(frame, city: str | None = None) -> dict:
    """Build UI option lists from the catalog; categories may be city-scoped."""
    local = frame
    if city:
        local = frame[frame["city"].map(normalized).eq(normalized(city))]
    return {
        "cities": _values(frame["city"]),
        "categories": _values(local["categories"]),
        "event_formats": _values(frame["event_formats"]),
        "languages": _values(frame["languages"]),
    }
