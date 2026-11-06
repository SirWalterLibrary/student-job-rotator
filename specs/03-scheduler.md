# 03 — Scheduler core (pure)

File: `rotator/scheduler.py`. No sqlite3, no Flask, no clock, no files. This exact code was simulated and verified;
copy it, do not "improve" it.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class JobInfo:
    id: int
    sort_order: int
    volunteers: tuple[int, ...]   # ACTIVE student ids, earliest volunteer first

LastServed = dict[int, dict[int, str]]   # job_id -> {student_id: 'YYYY-MM-DD' of last time they did that job}


def rank_key(job: JobInfo, student_id: int, last_served: LastServed) -> tuple[str, int]:
    """Never served ('') sorts first, then oldest date, then volunteer order."""
    return (last_served.get(job.id, {}).get(student_id, ""), job.volunteers.index(student_id))


def queue_order(job: JobInfo, last_served: LastServed, exclude=frozenset()) -> list[int]:
    """Volunteers of `job` in the order they will be picked, skipping `exclude`."""
    ids = [s for s in job.volunteers if s not in exclude]
    return sorted(ids, key=lambda s: rank_key(job, s, last_served))


def pick_session(jobs: list[JobInfo], last_served: LastServed,
                 locked: dict[int, int | None] | None = None) -> dict[int, int | None]:
    """Choose one student per job for ONE session. `locked` = job_id -> student_id already fixed."""
    result = dict(locked or {})
    busy = {s for s in result.values() if s is not None}
    todo = sorted((j for j in jobs if j.id not in result),
                  key=lambda j: (len(j.volunteers), j.sort_order, j.id))   # most constrained job first
    for job in todo:
        order = queue_order(job, last_served, exclude=busy)
        result[job.id] = order[0] if order else None
        if order:
            busy.add(order[0])
    return result


def record_picks(last_served: LastServed, date: str, picks: dict[int, int | None]) -> None:
    """Mutates last_served: remember who did each job on `date`. Skips None."""
    for job_id, student_id in picks.items():
        if student_id is not None:
            last_served.setdefault(job_id, {})[student_id] = date
```

## Why this is fair (explain this in the UI help text too)
- Per job, the person who waited longest goes next. Someone who has never had the job goes before anyone who has.
  So nobody repeats a job until every other available volunteer has had a turn.
- A new volunteer is "never served", so they get the next turn, then join the normal rotation.
- Rule 5 (one role per student per day) is hard. If the next person in line is already busy that day with another
  job, the next person after them is picked; the skipped person stays first in line next time.
- Jobs with fewer volunteers are filled first, so a job with a single volunteer is never blocked by a bigger job.
- Result is deterministic: same inputs → same schedule.

## Known consequences (document, don't "fix")
- A student who is the ONLY volunteer for a job is busy with it every session, so they will never be picked for other jobs.
  The "Up next" panel (06-ui) shows a hint for jobs with exactly one volunteer.
- Fairness is guaranteed per job. Because a student can volunteer for several jobs, their total number of turns across
  jobs can differ from others'.

## Worked examples
1. Fresh start, job 1 volunteers (A,B,C), no history → sessions pick A, B, C, A, B, C…
2. Most-constrained first: job "Dua" volunteers (Y); job "Adhan" volunteers (Y,M). Dua is filled first with Y;
   Adhan then skips busy Y and gets M. (`pick_session` → `{Dua: Y, Adhan: M}`)
3. New volunteer: job volunteers (A,B), last_served `{A:'2026-11-07', B:'2026-11-08'}`; C joins → C is next.
4. Locked: `locked={1: 7}` → job 1 is 7, and 7 is excluded from every other job that session.
5. Nobody free: all volunteers of a job are busy → `None` for that job. Job with zero volunteers → `None`.

## Tests (tests/test_scheduler.py) — all required
1. `test_fresh_queue_follows_volunteer_order`
2. `test_cycle_no_repeat_until_all_served` (3 volunteers, 9 sessions → each exactly 3 times, order A,B,C,A,B,C…)
3. `test_disjoint_jobs_counts_equal` (jobs with volunteers (1,2,3) and (4,5,6,7), 24 sessions: per job counts differ by ≤ 1)
4. `test_never_two_roles_same_day` (jobs: (1,2,3,4), (2,3,5), (1,5,6,7), (3,) over 60 sessions: picked students unique per session)
5. `test_most_constrained_job_first` (worked example 2)
6. `test_new_volunteer_goes_next` (worked example 3)
7. `test_job_without_volunteers_is_none`
8. `test_all_volunteers_busy_is_none`
9. `test_locked_rows_respected_and_exclude_student_elsewhere`
10. `test_deterministic` (same call twice → equal dicts)
11. `test_invariant_picked_is_oldest_available` (in the 60-session simulation of test 4: for every pick, no volunteer of that
    job who was not assigned elsewhere that day has an older `rank_key`)
12. `test_queue_order_excludes_busy`
Helper in tests: `days(n)` yielding the first n Saturdays/Sundays from 2026-11-07 as ISO strings.
