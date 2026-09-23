from datetime import date

import pandas as pd

from event_matcher.services.matching import find_matches


def provider(identifier, *, price=80_000, busy_dates="", formats="свадьба", languages="русский", hours=8, description="Ведущий на свадьбах и корпоративах.", **extra):
    row = {
        "id": identifier,
        "anon_name": f"Профиль {identifier}",
        "categories": "Ведущий",
        "city": "Астана",
        "city_imputed": False,
        "synthetic": False,
        "price_from_kzt": price,
        "price_imputed": False,
        "event_formats": formats,
        "languages": languages,
        "max_hours": hours,
        "busy_dates": busy_dates,
        "description": description,
    }
    row.update(extra)
    return row


def search(frame, **overrides):
    query = {
        "city": "Астана",
        "event_date": date(2026, 10, 15),
        "event_format": "свадьба",
        "category": "Ведущий",
        "budget_kzt": 100_000,
        "language": None,
        "hours": None,
    }
    query.update(overrides)
    return find_matches(pd.DataFrame(frame), **query)


def test_busy_provider_is_never_returned_and_top_results_capped_at_three():
    rows = [provider(f"HK-{n:04}") for n in range(5)]
    rows[0]["busy_dates"] = "2026-10-15|2026-10-20"

    result = search(rows)

    assert result["status"] == "matched"
    assert len(result["matches"]) == 3
    assert all(row["id"] != "HK-0000" for row in result["matches"])
    assert result["reasons"]["busy"] == 1


def test_no_category_differs_from_candidates_filtered_by_conditions():
    no_category = search([provider("one", categories="Фотограф")])

    assert no_category["status"] == "no_category"

    filtered = search([provider("one", busy_dates="2026-10-15")])

    assert filtered["status"] == "filtered_out"
    assert filtered["candidate_count"] == 1


def test_missing_language_or_duration_does_not_satisfy_requested_condition():
    result = search(
        [provider("one", languages="", hours=None)],
        language="казахский",
        hours=6,
    )

    assert result["status"] == "filtered_out"
    assert result["reasons"]["language"] == 1
    assert result["reasons"]["hours"] == 1


def test_ties_are_resolved_by_stable_identifier():
    rows = [provider("HK-2"), provider("HK-1")]

    first = search(rows)
    second = search(rows[::-1])

    assert [row["id"] for row in first["matches"]] == ["HK-1", "HK-2"]
    assert [row["id"] for row in first["matches"]] == [row["id"] for row in second["matches"]]


def test_profile_relevance_can_outrank_a_cheaper_weak_profile():
    rows = [
        provider("expensive", price=95_000, categories="host", formats="wedding", description="An experienced host for weddings."),
        provider("cheap", price=20_000, categories="host", formats="wedding", description="General profile with no event detail."),
    ]

    result = search(rows, category="host", event_format="wedding")

    assert [row["id"] for row in result["matches"]] == ["expensive", "cheap"]


def test_explanation_uses_profile_facts_and_imputation_flags():
    result = search([
        provider("HK-1", price=70_000, languages="русский|казахский", hours=8,
                 city_imputed=True, price_imputed=True, synthetic=True)
    ], language="казахский", hours=6)
    match = result["matches"][0]

    assert "казахский" in match["explanation"].lower()
    assert "не отмечена как занята в каталоге" in match["explanation"].lower()
    assert "6 ч" in match["explanation"]
    assert match["synthetic"] is True
    assert match["city_imputed"] is True
    assert match["price_imputed"] is True


def test_price_at_exact_budget_has_clear_explanation():
    result = search([provider("HK-1", price=100_000)], budget_kzt=100_000)

    assert "цена совпадает с бюджетом" in result["matches"][0]["explanation"].lower()
