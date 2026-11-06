# 04 — Schedule service (DB + scheduler glue)

Files: `rotator/schedule.py` (freeze + build), `rotator/actions.py` (swap, cancel, manual), `rotator/errors.py`.
Uses `scheduler.py` for picking and `dates.py` for calendar math. All functions take an open `conn` and a `today: date`.

```python
class RotatorError(Exception):
    def __init__(self, message: str, status: int = 400): ...
```
Routes turn `RotatorError` into `{"error": message}` with `status`.

## Loading helpers (schedule.py)
- `get_start_date(conn, today) -> date`: read setting `start_date`; if missing, store `first_class_day_on_or_after(today)` and return it.
- `load_jobs(conn) -> list[JobInfo]`: active jobs ordered by `sort_order, id`; `volunteers` = active students ordered by
  `joined_at, student_id`.
- `load_rows(conn) -> dict[str, dict[int, Row]]`: all assignments keyed by date then job_id.
- `cancelled_dates(conn) -> frozenset[date]`.

## The walker (single source of truth)
```python
def walk(conn, today: date, last_date: date, write: bool) -> dict[date, dict]:
    """Visit every held class day from start_date to last_date in order and return the result per day."""
```
For each class day `d` from `start_date` to `last_date`:
1. If `d` is cancelled → result `{"status": "cancelled"}`; no turns consumed; continue.
2. `existing` = stored rows on `d` as `{job_id: student_id}`.
3. If `d < today` and the session is frozen → picks = `existing` (never recompute).
4. Otherwise `picks = pick_session(jobs, last_served, locked=existing)`.
5. If `write` and `d <= today` and at least one job has volunteers: insert an `auto` row for every pick that has a student
   and no stored row yet; upsert `sessions(date, frozen=1)`.
   For `d == today` this runs on every call, so jobs/volunteers added later today get filled in
   (existing rows are never changed). Past days are frozen once and never touched again.
6. `record_picks(last_served, d.isoformat(), picks)` so later days see the history.
7. For `d > today`, rows are NOT written (projected), except stored locked rows that already exist.
`last_served` starts empty and is built only by this loop (stored rows on earlier dates feed it through step 4/3).

Frozen days that were skipped because the app was not opened are frozen in order the next time `freeze_through` runs.

```python
def freeze_through(conn, today) -> None      # walk(conn, today, today, write=True); call at the start of every read route
def build_sessions(conn, today, first: date, last: date) -> list[dict]
```
`build_sessions` calls `freeze_through`, then `walk(conn, today, last, write=False)`, then returns session views for class
days between `first` and `last` inclusive.

## Session view (what the API returns)
```json
{
  "date": "2026-11-07", "weekday": "Saturday", "status": "held",
  "is_today": true, "is_past": false, "note": "",
  "roles": [
    {"job": {"id": 1, "name": "Mu'adhin", "description": "Calls the adhan", "icon": "🕌"},
     "student": {"id": 3, "name": "Yusuf"},
     "source": "auto", "projected": false, "note": ""}
  ]
}
```
- `roles` has one entry per ACTIVE job (ordered by `sort_order, id`), `student: null` when nobody is available.
- Cancelled day: `"status": "cancelled"`, `"roles": []`, `note` = teacher's note.
- `projected` = true for future auto picks (not stored). `source` ∈ `auto|swap|manual`.
- `is_past` = date < today.
- Jobs that have no stored row on a past day are simply omitted from that day's roles (job added later).

## Queue status (for "Up next" panel)
`queue_status(conn, today) -> list[dict]`, one per active job:
```json
{"job": {"id":1,"name":"Mu'adhin"}, "volunteer_count": 4,
 "single_volunteer": false,
 "queue": [{"student": {"id":3,"name":"Yusuf"}, "turns": 2, "last_served": "2026-11-01"}, ...]}
```
`queue` = `queue_order(job, last_served_as_of_tomorrow)` (all volunteers, nobody excluded). `turns` = count of that
student's assignments to that job in the DB (any source). `last_served` = date or null.
`last_served_as_of_tomorrow` is built by running `walk` through the next class day after today and taking the dict it ends with.
(Expose the final `last_served` from the walker via a second return value or an out-parameter.)

## Actions (actions.py)
All require `date >= today` and `date` is a Saturday/Sunday; otherwise 400.

### swap_absent(conn, today, date, job_id, partner_id=None, vacant=False) -> dict
Teacher marks the student currently holding `job_id` on `date` (student A) as absent.
1. Load day `date` via `build_sessions`; A = student on that job; 404 if none. If `date` is cancelled → 409.
2. `vacant=True`: delete the stored row for (date, job) (freeze it first if `date` is today, so the row exists) and
   return. The job is empty that day; A stays first in the queue, so A naturally gets the next turn. No other change.
3. `N` = `next_class_day_after(date, cancelled)`. `C` = projected student for the same job on `N` (may be None).
4. Partner `B`:
   - if `partner_id` given: must be an active volunteer of the job, not A, and have no role on `date` → else 409.
   - else default: `C` if `C` exists, is not A and has no role on `date`; otherwise the first student of
     `queue_order(job, ..., exclude={A} ∪ students busy on date)`; if none → 409 "No available partner. Leave the job empty instead?"
5. A must have no other role on `N` (check the built session for N) → else 409.
6. If a `swap` or `manual` row already occupies (N, job) → 409 (no chained swaps).
7. In ONE transaction with a fresh `group_id` (uuid4 hex):
   - upsert (date, job) → B, source `swap`, note `"Covering for {A.name} (absent)"`
   - upsert (N, job) → A, source `swap`, note `"Make-up turn for {A.name} (absent on {date})"`
   (Upsert = replace the existing row for that slot; (date, student) unique index means do the date-row first,
   after deleting/updating whichever row B currently holds on that date, which cannot exist because B has no role on `date`.)
8. Return `{"date": date, "next_date": N, "covering": B, "absent": A}`.
Effect: B's last_served for the job becomes `date`, A's becomes `N`; C (if different from B) is displaced one turn and is
first in line afterwards.

### cancel_session(conn, today, date, note="") -> None
Teacher away. `date >= today`.
1. Upsert `sessions(date, status='cancelled', note)`.
2. Delete ALL assignments on `date`. For every deleted row with a `group_id`, also delete the other rows with that
   `group_id` (the swap counterpart on another day).
3. Nothing else. Because cancelled days consume no turns, every projected assignment on later days recomputes, so each
   student's turn moves to the next held class day. Cancelling both Saturday and Sunday skips the whole weekend.
4. Cancelling an already-cancelled day → 409.

### restore_session(conn, today, date) -> None
Set status `held`, clear note. If `date == today`, the next read re-fills the day (walker step 5). 409 if not cancelled.

### set_manual(conn, today, date, job_id, student_id) -> None
Teacher override. Student must be an active volunteer of the job and have no role on `date` (or already hold that same job).
Day must be held. Upsert (date, job) with source `manual`, empty note. Replaces whatever row was there. If the replaced row
had a `group_id`, delete its counterpart too.

### clear_assignment(conn, today, date, job_id) -> None
Delete the stored row for (date, job) (and its `group_id` counterpart). For a projected future slot with no stored row → 404.
(Meaning: for today, "leave empty"; for a future day, undo a swap/manual lock.)

## Roster side effects (see 01 archive rules; implemented in the roster module, T04)
`today` is needed to delete future rows, so roster routes call `request_today()`.

## Required tests (tests/test_schedule.py, tests/test_actions.py) — use today override, never the real clock
- first walk freezes today's Saturday with one auto row per job; second call changes nothing
- Friday 2026-11-06 view shows Sat 11-07 and Sun 11-08 as projected; nothing stored for them
- Saturday then Sunday: nobody has two roles on the same day (multi-job roster)
- sequence over 4 weekends gives each volunteer of a 3-person job a turn before anyone repeats
- adding a volunteer on Wednesday changes next Saturday's projection (new person first) but not past frozen days
- swap: A absent Sat → B covers Sat, A holds the job Sun; B's later turns follow queue (C displaced, goes next)
- swap rejects: partner already busy; A busy on next day; occupied locked slot; past date
- vacant: row removed, A is next in queue the following session
- cancel Sat: Sat has no roles, Sunday's projection equals what Saturday's would have been (shifted)
- cancel Sat with a swap whose counterpart is on Sunday → both rows gone
- restore Sat → roles reappear and turns shift back
- Sat→Sun→next Sat: `next_class_day_after` with cancelled Sunday skips to next Saturday
- manual: rejects non-volunteer, rejects student who already has another role that day
- DST weekend 2026-11-01 (Sunday): walk works across it (no off-by-one)
