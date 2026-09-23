from pathlib import Path

import pandas as pd

from ..config import DATA_PATH, REQUIRED_COLUMNS


def load_catalog(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load the CSV catalog using a path anchored to the project, not cwd."""
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Не найден файл каталога: {path}")

    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(
            f"В каталоге {path} отсутствуют обязательные столбцы: "
            + ", ".join(sorted(missing))
        )

    text_columns = (
        "id", "anon_name", "categories", "city", "event_formats",
        "languages", "busy_dates", "description",
    )
    for column in text_columns:
        frame[column] = frame[column].fillna("").astype(str)
    for column in ("price_from_kzt", "max_hours"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame
