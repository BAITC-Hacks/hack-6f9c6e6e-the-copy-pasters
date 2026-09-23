# EventMatch KZ Web Application Implementation Plan

> **For agentic workers:** Implement this plan task by task using the inline execution flow and test-driven development.

**Goal:** Replace the Streamlit MVP with a modular FastAPI service and a compact responsive HTML/CSS/JavaScript website that returns up to three grounded contractor matches.

**Architecture:** FastAPI serves both the static page and same-origin JSON endpoints. A CSV repository loads the existing catalog by project-relative path; focused matching and explanation services consume the normalized dataframe. The browser only handles form state and renders typed API results.

**Tech Stack:** Python, FastAPI, Uvicorn, pandas, Pydantic, pytest, HTTPX2, semantic HTML, CSS, vanilla JavaScript.

**Spec:** `docs/superpowers/specs/2026-09-23-event-match-web-design.md`

## Global Constraints

- Backend: FastAPI; frontend: ordinary HTML, CSS and JavaScript without a separate frontend framework.
- `data.csv` remains the catalog source; do not change source data without necessity.
- Do not use external AI services, paid APIs, or generated explanations.
- Return no more than three results.
- A contractor busy on the selected date is excluded as a hard rule.
- Language and duration are optional search conditions; if supplied, both must match verified profile data.
- Keep `no_category` distinct from `filtered_out`.
- Mark synthetic profiles and imputed city/price in visible text.
- No booking, messages, payments, accounts, or database.

## Review Focus

- Busy-date parsing and exact-day exclusion, including empty and multi-date values.
- Missing requested language or duration is not treated as a match.
- Equivalent queries have deterministic ordering when scores tie.
- Explanations never claim facts absent from profile fields.
- CSV lookup is independent of process working directory and surfaces missing schema clearly.

## File Structure

```text
app.py                                  Uvicorn entry point
event_matcher/api/routes.py             options and match HTTP endpoints
event_matcher/api/application.py        FastAPI app factory and static page route
event_matcher/api/schemas.py            validated request and response models
event_matcher/repositories/catalog.py   project-relative CSV load/normalization
event_matcher/services/catalog.py       options derived from catalog
event_matcher/services/matching.py      filters, deterministic ranking, explanations
event_matcher/__init__.py               package marker
static/index.html                       labeled search form and results region
static/css/styles.css                   warm neutral/terracotta responsive styles
static/js/app.js                        form requests, validation messages, safe rendering
tests/test_catalog.py                   repository and options behavior
tests/test_matching.py                  filters, outcomes, ordering, fact-grounded copy
tests/test_api.py                       HTTP behavior and validation
requirements.txt                        runtime and test dependencies
README.md                               install, launch, demo and limits
ARCHITECTURE.md                         final component/data flow
```

## Task 1: CSV Repository and Matching Service

**Files:** Create `event_matcher/repositories/catalog.py`, `event_matcher/services/catalog.py`, `event_matcher/services/matching.py`, `tests/test_catalog.py`, `tests/test_matching.py`; create package marker files if absent.

**Interfaces:** `load_catalog(path: Path = DATA_PATH) -> pandas.DataFrame`; `get_options(df, city: str | None = None) -> dict`; `find_matches(df, *, city: str, event_date: date, event_format: str, category: str, budget_kzt: int, language: str | None = None, hours: int | None = None) -> dict`.

- [x] Write repository tests for loading the project CSV regardless of current directory, required-column errors, and city-scoped categories.
- [x] Run `py -m pytest tests/test_catalog.py -q`; expect failure because the repository service does not exist yet.
- [x] Implement project-relative CSV loading, schema validation against `REQUIRED_COLUMNS`, type normalization, and catalog-derived options.
- [x] Run `py -m pytest tests/test_catalog.py -q`; expect all repository tests to pass.
- [x] Write matching tests for busy-date exclusion, the three outcomes, requested-language/duration missing-data exclusion, score ranking and stable-ID tie breaking, max-three output, and profile-grounded explanations/flags.
- [x] Run `py -m pytest tests/test_matching.py -q`; expect failure because the matching service does not exist yet.
- [x] Implement filters first, then deterministic score (`description/profile relevance`, verified requested conditions, price), stable ID tie-break, and up to three response dictionaries. Reuse the existing lexical term map and description excerpt logic; do not reuse any explanation that makes unsupported claims.
- [x] Run `py -m pytest tests/test_catalog.py tests/test_matching.py -q`; expect the focused suite to pass.

## Task 2: FastAPI Routes and Validation

**Files:** Replace Streamlit contents of `app.py`; create `event_matcher/api/application.py`, `event_matcher/api/routes.py`, `event_matcher/api/schemas.py`, `tests/test_api.py`; modify `requirements.txt`.

**Interfaces:** `create_app(catalog_path: Path = DATA_PATH) -> FastAPI` in `event_matcher/api/application.py`; `GET /api/options?city=...`; `POST /api/match` with fields from the spec; `GET /` serves `static/index.html`.

- [x] Write API tests using `starlette.testclient.TestClient` for successful options/search, `no_category`, `filtered_out`, invalid budget/date/hours returning 422, and the up-to-three response contract.
- [x] Run `py -m pytest tests/test_api.py -q`; expect failure because FastAPI app/endpoints are not implemented.
- [x] Add `fastapi`, `uvicorn[standard]`, `pandas`, `pytest`, and `httpx2` to requirements with compatible lower bounds; remove Streamlit.
- [x] Implement request/response Pydantic models, app factory with startup CSV loading, API routes, explicit status responses, and static index route. A bad or missing CSV must fail startup with a clear path/schema error.
- [x] Run `py -m pytest tests/test_api.py -q`; expect all API tests to pass.
- [x] Run `py -m pytest -q`; expect all repository, matching, and API tests to pass.

## Task 3: Website, Documentation, and End-to-End Verification

**Files:** Create `static/index.html`, `static/css/styles.css`, `static/js/app.js`; replace `README.md` and `ARCHITECTURE.md`.

**Interfaces:** Frontend reads options from `/api/options` and posts the form to `/api/match`; all result rendering uses text nodes/textContent, not interpolated HTML.

- [x] Add static-serving tests that assert the homepage is served, form labels and result live region exist, and stylesheet/script references are present.
- [x] Run `py -m pytest tests/test_api.py -q`; expect the new static assertions to fail until the page is authored.
- [x] Implement a responsive labeled form for city, date, event format, category, budget, optional language and optional hours; keep all catalog categories selectable and label those absent from the selected city so `no_category` is reachable; preserve inputs and announce errors/results through accessible live regions.
- [x] Render at most three compact result rows with names, categories, price, availability, concrete explanation, and visible synthetic/imputed labels. Render the two distinct empty outcomes and retryable network errors.
- [x] Style with a warm neutral surface, dark text, quiet dividers and one terracotta accent; add narrow-screen rows, keyboard focus, sufficient contrast, and no gradient/glass/emoji icons.
- [x] Run `py -m pytest -q`; expect all tests to pass.
- [x] Update README with Windows setup, `py -m venv .venv`, activation, `py -m pip install -r requirements.txt`, `py -m uvicorn app:app --reload`, correct localhost URL, scenarios and limitations. Update architecture diagram to the implemented modules.
- [x] Launch the app from outside the project directory and verify the home page and API load; perform one matched search, one busy-date search, one missing-category search, and one filtered-out search using the available browser.
- [x] Re-run `py -m pytest -q`; expect the complete suite to pass.

## Execution Notes

The supplied folder is not a Git repository, so isolated Git worktrees and per-task commits are unavailable. Keep the source CSV untouched, record task progress in `.superpowers/sdd/2026-09-23-event-match-web-implementation/progress.md`, and report that changes are uncommitted files.

