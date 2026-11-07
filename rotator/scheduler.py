"""Pure, deterministic session picker (no database, clock, files, or randomness)."""
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
