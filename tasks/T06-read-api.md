# T06 — Read API: config, today, calendar, queue

Depends on: T05.
Read: `AGENTS.md`, `specs/05-api.md` (Read routes + "Behavior every read route shares"), `specs/04-schedule-service.md` (Session view).

## Create
- `rotator/routes_schedule.py` — blueprint with `GET /api/config`, `/api/today`, `/api/calendar`, `/api/queue`.
  Each route: `today = request_today()`, `conn = get_conn()`, then `build_sessions(...)` (it freezes first).
- Register the blueprint in `create_app`.
- `tests/test_routes_schedule.py`

## Behavior (from 05)
- `/api/today`: Mon–Fri → `mode "upcoming"`, heading "Next weekend", two sessions (`upcoming_weekend`). Sat/Sun → `mode "today"`,
  heading "Today", one session. `next_held` only when all returned sessions are cancelled: it is the session view of
  `next_class_day_after(last returned date, cancelled)`.
- `/api/calendar?month=YYYY-MM`: sessions for every Sat/Sun in that month on/after `start_date`.
  Window: month of `start_date` ≤ month ≤ 24 months after today. Outside → 400 `{"error": ...}`. Bad format → 400.
  `prev`/`next` per 05. `label` like "November 2026" (English month names; don't use locale-dependent `strftime`
  — use a fixed list of month names).
- `/api/config`: includes `pin_required` (true if `ADMIN_PIN` non-empty) and `start_date` (calls `get_start_date`).
- `/api/queue`: `{"jobs": queue_status(...)}`.

## Tests (use `?today=` with ALLOW_TODAY_OVERRIDE; seed a roster with helpers)
- config on 2026-11-06: weekday "Friday", `start_date` "2026-11-07", pin_required false
- today Friday → upcoming with Saturday 11-07 and Sunday 11-08, `projected` true, `is_today` false
- today Saturday → one session, `is_today` true, `projected` false, rows stored in DB
- today Sunday → one session (Sunday)
- today Monday 2026-11-09 → 11-14 and 11-15
- calendar November 2026 has 8 sessions (7, 8, 14, 15, 21, 22, 28, 29), `prev` null (month of start), `next` "2026-12"
- calendar month before start → 400; month 25 months out → 400; garbage → 400; missing month → current month
- all `/api` responses have `Cache-Control: no-store`
- empty roster: today returns sessions with `roles: []`, no errors
- cancelled Saturday (insert into `sessions` directly) with today = Saturday → the one returned session has `status "cancelled"`,
  so `next_held` is Sunday's session view; with today = Friday only Saturday is cancelled, so `next_held` is null

## Done when
`pytest -q` passes. With `ALLOW_TODAY_OVERRIDE=1 flask run` and a seeded DB, `curl localhost:5055/api/today?today=2026-11-06` returns JSON.

## Don't
Implement mutating actions or the frontend.
