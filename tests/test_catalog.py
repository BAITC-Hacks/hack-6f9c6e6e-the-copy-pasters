from pathlib import Path

import pandas as pd
import pytest

from event_matcher.repositories.catalog import load_catalog
from event_matcher.services.catalog import get_options


def test_load_catalog_resolves_path_relative_to_project(tmp_path: Path):
    source = Path(__file__).resolve().parents[1] / "data.csv"
    frame = load_catalog(source)

    assert len(frame) > 0
    assert {"id", "city", "busy_dates", "synthetic", "city_imputed", "price_imputed"} <= set(frame.columns)


def test_default_catalog_path_does_not_depend_on_current_directory(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert len(load_catalog()) > 0


def test_load_catalog_reports_missing_required_columns(tmp_path: Path):
    path = tmp_path / "broken.csv"
    pd.DataFrame({"id": ["x"]}).to_csv(path, index=False)

    with pytest.raises(ValueError) as error:
        load_catalog(path)
    assert "broken.csv" in str(error.value)


def test_options_are_derived_from_selected_city():
    frame = pd.DataFrame({
        "city": ["Астана", "Алматы"],
        "categories": ["Ведущий|Фотограф", "Флорист"],
        "event_formats": ["свадьба|корпоратив", "свадьба"],
        "languages": ["русский|казахский", "русский"],
    })

    options = get_options(frame, city="Астана")

    assert options["categories"] == ["Ведущий", "Фотограф"]
    assert options["cities"] == ["Алматы", "Астана"]
    assert options["languages"] == ["казахский", "русский"]
