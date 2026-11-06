# T05 — Schedule service: freeze + build sessions

Depends on: T01, T02, T03, T04.
Read: `AGENTS.md`, `specs/04-schedule-service.md` (everything above "Actions"), `specs/03-scheduler.md` (API only), `specs/02-dates.md`.

## Create
- `rotator/schedule.py`: `get_start_date`, `load_jobs`, `load_rows`, `cancelled_dates`, `walk`, `freeze_through`,
  `build_sessions`, `queue_status` — exactly as described in 04.
- `tests/helpers.py`: small functions to seed a roster in tests (`make_students(conn, names)`, `make_job(conn, name, student_ids)`).
- `tests/test_schedule.py`

## Implementation notes
- `walk` is the only place that loops over days. `freeze_through` and `build_sessions` both call it.
- Return `(results, last_served)` from `walk` so `queue_status` can reuse the final `last_served`.
- The session view dict has the exact shape in 04 (weekday names in English, `roles` ordered by job `sort_order, id`).
- Never store future auto rows. Only `d <= today` writes happen.
- `get_start_date` writes the setting the first time it is called.

## Tests (the schedule-related ones from 04)
- first freeze writes one auto row per job for today's Saturday; second call writes nothing new
- Friday view: Sat/Sun projected, `SELECT COUNT(*) FROM assignments` is 0 afterwards
- multi-job roster over 12 weekends: nobody has two roles on a day
- a 3-person job rotates A,B,C,A,B,C across consecutive class days (single-job roster)
- adding a volunteer on a weekday changes the next Saturday projection (new person first) but a frozen past day is untouched
- missed weeks: app first used on 2026-11-22 with start_date 2026-11-07 → days 11-07, 08, 14, 15, 21 are frozen in order
- `queue_status` lists volunteers in the right order with `turns` and `last_served`, flags `single_volunteer`
- cancelled day inserted directly into `sessions` is skipped by `walk` (no turns consumed)
- job added later today is filled into today's already-frozen session (existing rows unchanged)

## Done when
`pytest -q` passes.

## Don't
Implement swap/cancel actions (T07) or HTTP routes (T06).
