# T08 — Admin PIN, rate limit, export/import

Depends on: T04, T07.
Read: `AGENTS.md`, `specs/05-api.md` (Auth, Admin routes), `specs/08-deployment.md` (Safety).

## Create / change
- `rotator/auth.py`:
  - `pin_ok(app_config, provided: str) -> bool` using `hmac.compare_digest`; if no PIN configured → True.
  - in-memory failure limiter `FailureLimiter(max_failures=5, window_seconds=60)` with `blocked(key)`, `record(key)`.
    Key = client IP. Time source is injectable for tests (`now()` callable).
- `rotator/routes_common.py`: replace the no-op `require_pin` with a real decorator: reads `X-Admin-Pin`; missing/wrong → 401
  `{"error": "Teacher PIN required"}`; blocked IP → 429. Wrong PINs count as failures. When no PIN is configured it passes.
- `rotator/routes_admin.py`: `POST /api/auth`, `GET /api/export`, `POST /api/import` (spec in 05).
- If `TRUST_PROXY` → wrap `app.wsgi_app` with `werkzeug.middleware.proxy_fix.ProxyFix(x_for=1)`.
- Apply `@require_pin` to every mutating route (roster, actions, settings, import) and to export. GET read routes stay public.
- `tests/test_auth.py`, `tests/test_backup.py`

## Tests
- with PIN set: mutating route without header → 401; wrong → 401; right → 200; GET `/api/today` works without PIN
- no PIN configured: mutating route works without header
- `POST /api/auth` right/wrong; 5 wrong in a minute then right PIN → 429; after the window (fake clock) works again
- `/api/export` requires PIN; export → import into a fresh app → `/api/calendar` JSON identical (use same `?today`)
- import with `version` 2 → 400 and database unchanged; import with garbage → 400 and database unchanged
- `hmac.compare_digest` is used (grep check in test is optional)

## Done when
`pytest -q` passes (including all earlier tests — update earlier tests to send the header only where they set a PIN; default test app has no PIN).

## Don't
Store the PIN in the database or log it.
