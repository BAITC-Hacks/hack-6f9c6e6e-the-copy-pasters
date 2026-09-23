import pandas as pd
import pytest
from starlette.testclient import TestClient

from event_matcher.api.application import create_app


@pytest.fixture
def catalog_path(tmp_path):
    path = tmp_path / "data.csv"
    pd.DataFrame([
        {
            "id": "HK-1", "anon_name": "Профиль один", "categories": "Ведущий",
            "city": "Астана", "city_imputed": False, "synthetic": False,
            "price_from_kzt": 80_000, "price_imputed": False,
            "event_formats": "свадьба", "languages": "русский|казахский",
            "max_hours": 8, "busy_dates": "2026-10-20",
            "description": "Ведущий мероприятий и свадеб.",
        },
        {
            "id": "HK-2", "anon_name": "Профиль два", "categories": "Фотограф",
            "city": "Астана", "city_imputed": True, "synthetic": True,
            "price_from_kzt": 40_000, "price_imputed": True,
            "event_formats": "корпоратив", "languages": "русский",
            "max_hours": None, "busy_dates": "",
            "description": "Фотограф мероприятий.",
        },
    ]).to_csv(path, index=False)
    return path


@pytest.fixture
def client(catalog_path):
    with TestClient(create_app(catalog_path)) as test_client:
        yield test_client


def test_options_and_search_return_profile_facts_and_flags(client):
    options = client.get("/api/options", params={"city": "Астана"})
    result = client.post("/api/match", json={
        "city": "Астана", "event_date": "2026-10-15", "event_format": "свадьба",
        "category": "Ведущий", "budget_kzt": 100_000, "language": "казахский", "hours": 6,
    })

    assert options.status_code == 200
    assert options.json()["categories"] == ["Ведущий", "Фотограф"]
    assert result.status_code == 200
    assert result.json()["status"] == "matched"
    assert result.json()["matches"][0]["synthetic"] is False
    assert result.json()["matches"][0]["explanation"]


def test_busy_date_and_two_distinct_empty_states(client):
    busy = client.post("/api/match", json={
        "city": "Астана", "event_date": "2026-10-20", "event_format": "свадьба",
        "category": "Ведущий", "budget_kzt": 100_000,
    }).json()
    no_category = client.post("/api/match", json={
        "city": "Астана", "event_date": "2026-10-15", "event_format": "свадьба",
        "category": "Флорист", "budget_kzt": 100_000,
    }).json()

    assert busy["status"] == "filtered_out"
    assert busy["reasons"]["busy"] == 1
    assert no_category["status"] == "no_category"


def test_invalid_search_values_return_422(client):
    response = client.post("/api/match", json={
        "city": "Астана", "event_date": "not-a-date", "event_format": "свадьба",
        "category": "Ведущий", "budget_kzt": 0, "hours": 25,
    })

    assert response.status_code == 422


def test_homepage_contains_labeled_form_live_region_and_asset_links(client):
    response = client.get("/")
    stylesheet = client.get("/static/css/styles.css")
    script = client.get("/static/js/app.js")

    assert response.status_code == 200
    for field in ("city", "event-date", "event-format", "category", "budget", "language", "hours"):
        assert f'for="{field}"' in response.text
    assert 'id="budget" name="budget_kzt" type="number" min="1" max="100000000" step="1" value="900000"' in response.text
    assert 'aria-live="polite"' in response.text
    assert "/static/css/styles.css" in response.text
    assert "/static/js/app.js" in response.text
    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert ".innerHTML" not in script.text
    assert "нет в городе" in script.text


def test_missing_catalog_fails_startup_with_path(tmp_path):
    missing_path = tmp_path / "missing.csv"
    with pytest.raises(RuntimeError, match="missing.csv"):
        with TestClient(create_app(missing_path)):
            pass
