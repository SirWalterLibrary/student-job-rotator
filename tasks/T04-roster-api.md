# T04 — Roster API: students, jobs, volunteers

Depends on: T01, T02.
Read: `AGENTS.md`, `specs/05-api.md` (Roster routes + the two list GETs), `specs/01-data-model.md` (Archive rules).

## Create
- `rotator/roster.py` — DB functions (no Flask): `list_students`, `add_student`, `rename_student`, `archive_student`,
  `list_jobs`, `add_job`, `update_job`, `archive_job`, `reorder_jobs`, `set_volunteers`. Each takes `conn` (and `today` where
  archive rules need it). Raise `RotatorError` for validation (400) and conflicts (409).
- `rotator/routes_roster.py` — blueprint with the routes in 05. For now `require_pin` is a no-op decorator in
  `routes_common.py` (T08 makes it real); apply it to every mutating route already.
- Register the blueprint in `create_app`.
- `tests/test_roster.py`

## Rules to implement
- Name rules and duplicate handling exactly as in 05 (trim, length, case-insensitive duplicates, re-activate archived).
- Archive student: set `active=0`, delete their `volunteers`, delete their `assignments` with `date > today`.
- Archive job: set `active=0`, delete its `assignments` with `date > today`.
- `set_volunteers`: keep `joined_at` for existing, `utc_now_iso()` for new, delete removed; reject archived/unknown ids (400).
  Use a distinct timestamp per new id by iterating in the order given (microseconds differ; if equal, student id breaks ties later).
- `reorder_jobs` ids must equal the set of active job ids.
- `GET /api/jobs` includes `volunteer_ids` ordered by `joined_at, student_id`.

## Tests
- add/list/rename/archive student; duplicate name 409; re-add archived name reactivates same id; empty name 400; 41 chars 400
- add job with volunteers; update; archive; reorder; reorder with wrong ids 400
- `PUT volunteers` adds, removes, keeps existing `joined_at`; archived student 400
- archiving a student removes them from every job's `volunteer_ids`
- archiving a student deletes a future assignment row (insert one with SQL for date 2026-11-14 with `today` override 2026-11-06)
  but keeps a past one
- `include_archived=1` shows archived items

## Done when
`pytest -q` passes.

## Don't
Implement scheduling, auth checks or UI.
