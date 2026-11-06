# T00 — Scaffold, config, health endpoint, pytest fixtures

Depends on: nothing.
Read: `AGENTS.md`, `specs/01-data-model.md` (Config section), `specs/05-api.md` (top section only), `specs/08-deployment.md` (requirements, wsgi).

## Create
- `git init` (if not already), `.gitignore` (`.venv/ data/ __pycache__/ *.pyc .env .pytest_cache/`)
- `requirements.txt`, `wsgi.py` (exact contents in 08)
- `rotator/__init__.py` (empty)
- `rotator/config.py`: `load_config(overrides: dict | None = None) -> dict` reading the env vars in 01, with defaults.
  `ALLOW_TODAY_OVERRIDE`, `TRUST_PROXY` → bool; `DATA_DIR` → str.
- `rotator/errors.py`: `RotatorError(message, status=400)` (see 04).
- `rotator/app.py`: `create_app(config=None)`:
  - builds config via `load_config`, creates `DATA_DIR` if missing
  - if `APP_ENV == "production"` and `ADMIN_PIN` empty → `raise RuntimeError("ADMIN_PIN must be set when APP_ENV=production")`
  - registers an error handler: `RotatorError` → JSON `{"error": msg}` + status; unknown `/api/*` 404 → JSON; 500 → JSON `{"error":"Server error"}`
  - route `GET /api/health` → `{"ok": true}`
  - route `GET /` → serves `rotator/static/index.html` (create a placeholder `index.html` containing `<h1>Khidmah Roster</h1>`)
  - `Cache-Control: no-store` on all `/api/` responses (use `after_request`)
- `tests/conftest.py`: fixtures `app` (uses `tmp_path` as `DATA_DIR`, `ADMIN_PIN=""`, `ALLOW_TODAY_OVERRIDE=True`) and `client`.
- `tests/test_app.py`

## Tests
- `test_health_ok`
- `test_index_served`
- `test_unknown_api_route_is_json_404`
- `test_production_requires_pin` (create_app with `APP_ENV=production`, empty PIN → RuntimeError; with PIN → fine)
- `test_api_responses_not_cached` (header `Cache-Control: no-store` on `/api/health`)

## Done when
- `pip install -r requirements.txt` succeeds in a fresh `.venv`
- `pytest -q` passes (5 tests)
- `DATA_DIR=./data flask --app wsgi run --port 5055` serves `/api/health`

## Don't
Add a database, scheduler or any other feature.
