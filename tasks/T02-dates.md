# T02 — Dates module (Central time, class days)

Depends on: T00.
Read: `AGENTS.md`, `specs/02-dates.md`.

## Create
- `rotator/dates.py` with every function listed in 02 (signatures and behavior exactly as written).
- `rotator/routes_common.py`: `request_today() -> date`. Uses `flask.request`/`current_app`:
  if `current_app.config["ALLOW_TODAY_OVERRIDE"]` is true and `?today=YYYY-MM-DD` is present and valid → that date;
  invalid value → raise `RotatorError("Invalid today parameter", 400)`; otherwise `central_today()`.
- `tests/test_dates.py`, `tests/test_today_override.py`

## Tests (use the reference dates in 02)
- `test_upcoming_weekend_friday`, `_saturday`, `_sunday`, `_monday`
- `test_next_class_day_after_sat_sun_sat`
- `test_next_class_day_after_skips_cancelled`
- `test_class_days_range_inclusive` (2026-11-01..2026-11-30 → 2026-11-01, 07, 08, 14, 15, 21, 22, 28, 29)
- `test_month_class_days_november_2026`
- `test_first_class_day_on_or_after`
- `test_central_today_dst_end_utc_is_monday` / `test_central_today_saturday_late_night` / `test_central_today_dst_start`
- `test_central_today_rejects_naive_datetime`
- `test_override_ignored_when_disabled`, `test_override_used_when_enabled`, `test_override_invalid_400`
  (temporary test route registered on a test app, or call `request_today` inside `app.test_request_context`)

## Done when
`pytest -q` passes. `grep -rn "date.today\|datetime.now()" rotator/` prints nothing (only `datetime.now(TZ)` is allowed).

## Don't
Touch the database or add routes other than what's listed.
