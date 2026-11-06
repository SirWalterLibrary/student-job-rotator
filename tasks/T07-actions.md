# T07 — Actions: absent swap, cancel/restore day, manual override

Depends on: T05, T06.
Read: `AGENTS.md`, `specs/04-schedule-service.md` (the "Actions" section and the tests list), `specs/05-api.md` (Action routes).

## Create
- `rotator/actions.py`: `swap_absent`, `cancel_session`, `restore_session`, `set_manual`, `clear_assignment` — follow the numbered
  steps in 04 literally. Wrap multi-row writes in a single transaction (`with conn:`).
- `rotator/routes_actions.py`: the routes in 05 (`absent`, `cancel`, `restore`, `assignments` PUT/DELETE, `PUT /api/settings`).
  `PUT/DELETE assignments` return the session view for that date via `build_sessions`.
- Register blueprint. Add `set_start_date` logic to `schedule.py` (validation in 05: Sat/Sun; not after any frozen session → 409).
- `tests/test_actions.py` — all action tests listed at the bottom of 04, written with `?today=` overrides.

## Implementation hints
- Freeze before acting: call `freeze_through(conn, today)` first so today's stored rows exist.
- To find who holds a job on a day, use `build_sessions(conn, today, d, d)[0]["roles"]`.
- Swap on today's row: update the existing `auto` row in place (change `student_id`, `source='swap'`, `note`, `group_id`).
  Swap on the next day: insert a new row (`swap`). If a projected slot is displaced, nothing is stored for it.
- `UNIQUE(date, student_id)`: B has no row on `date` (checked), so updating the (date, job) row to B never collides.
- Return errors via `RotatorError` with the exact statuses from 04/05.

## Done when
`pytest -q` passes. Manual check with curl on a seeded DB: absent on Saturday, then `GET /api/today?today=2026-11-07`
shows the swap chip data (`source: "swap"`, note text) and `GET /api/calendar?month=2026-11&today=2026-11-07` shows the absent student on Sunday.

## Don't
Add auth (T08) or frontend work.
