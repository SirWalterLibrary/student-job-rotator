"""Tests for the pure scheduler (all 12 required by spec 03)."""
from collections import Counter
from datetime import date, timedelta

from rotator.scheduler import JobInfo, LastServed, pick_session, queue_order, rank_key, record_picks


def days(n: int) -> list[str]:
    """First n Saturdays/Sundays from 2026-11-07 as ISO strings."""
    out: list[str] = []
    d = date(2026, 11, 7)
    while len(out) < n:
        if d.weekday() in (5, 6):
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def test_fresh_queue_follows_volunteer_order():
    """With no history, the queue is the volunteer order."""
    job = JobInfo(1, 0, (1, 2, 3))
    assert queue_order(job, {}) == [1, 2, 3]


def test_cycle_no_repeat_until_all_served():
    """3 volunteers over 9 sessions rotate A, B, C with each serving exactly 3 times."""
    job = JobInfo(1, 0, (1, 2, 3))
    last: LastServed = {}
    picked = []
    for d in days(9):
        picks = pick_session([job], last)
        picked.append(picks[1])
        record_picks(last, d, picks)
    assert picked == [1, 2, 3, 1, 2, 3, 1, 2, 3]
    assert Counter(picked) == {1: 3, 2: 3, 3: 3}


def test_disjoint_jobs_counts_equal():
    """Over 24 sessions, per-job volunteer counts differ by at most one."""
    jobs = [JobInfo(1, 0, (1, 2, 3)), JobInfo(2, 1, (4, 5, 6, 7))]
    last: LastServed = {}
    counts: dict[int, Counter] = {1: Counter(), 2: Counter()}
    for d in days(24):
        picks = pick_session(jobs, last)
        for job_id, student_id in picks.items():
            if student_id is not None:
                counts[job_id][student_id] += 1
        record_picks(last, d, picks)
    assert max(counts[1].values()) - min(counts[1].values()) <= 1
    assert max(counts[2].values()) - min(counts[2].values()) <= 1


def test_never_two_roles_same_day():
    """Overlapping volunteer lists never put a student on two jobs in one session."""
    jobs = [JobInfo(1, 0, (1, 2, 3, 4)), JobInfo(2, 1, (2, 3, 5)),
            JobInfo(3, 2, (1, 5, 6, 7)), JobInfo(4, 3, (3,))]
    last: LastServed = {}
    for d in days(60):
        picks = pick_session(jobs, last)
        taken = [s for s in picks.values() if s is not None]
        assert len(taken) == len(set(taken))
        record_picks(last, d, picks)


def test_most_constrained_job_first():
    """Worked example 2: single-volunteer Dua is filled first, Adhan skips busy Y."""
    jobs = [JobInfo(1, 0, (9,)), JobInfo(2, 1, (9, 8))]
    picks = pick_session(jobs, {})
    assert picks == {1: 9, 2: 8}


def test_new_volunteer_goes_next():
    """Worked example 3: a brand-new volunteer (never served) is picked next."""
    job = JobInfo(1, 0, (1, 2, 3))
    last: LastServed = {1: {1: "2026-11-07", 2: "2026-11-08"}}
    assert pick_session([job], last)[1] == 3


def test_job_without_volunteers_is_none():
    """A job with zero volunteers gets None."""
    picks = pick_session([JobInfo(1, 0, ())], {})
    assert picks == {1: None}


def test_all_volunteers_busy_is_none():
    """When every volunteer is already busy that day, the job gets None."""
    jobs = [JobInfo(1, 0, (5,)), JobInfo(2, 1, (5,))]
    picks = pick_session(jobs, {})
    assert picks == {1: 5, 2: None}


def test_locked_rows_respected_and_exclude_student_elsewhere():
    """Worked example 4: locked rows stick and lock that student out of other jobs."""
    jobs = [JobInfo(1, 0, (7, 1, 2)), JobInfo(2, 1, (7, 3, 4))]
    picks = pick_session(jobs, {}, locked={1: 7})
    assert picks == {1: 7, 2: 3}


def test_deterministic():
    """Same inputs produce equal results on repeated calls."""
    jobs = [JobInfo(1, 0, (1, 2, 3, 4)), JobInfo(2, 1, (2, 3, 5)), JobInfo(3, 2, (1, 5, 6, 7))]
    last: LastServed = {1: {1: "2026-11-07"}, 3: {6: "2026-11-01"}}
    a = pick_session(jobs, dict(last))
    b = pick_session(jobs, dict(last))
    assert a == b


def test_invariant_picked_is_oldest_available():
    """In the 60-session simulation, every pick has the oldest rank_key among available volunteers."""
    jobs = [JobInfo(1, 0, (1, 2, 3, 4)), JobInfo(2, 1, (2, 3, 5)),
            JobInfo(3, 2, (1, 5, 6, 7)), JobInfo(4, 3, (3,))]
    last: LastServed = {}
    for d in days(60):
        picks = pick_session(jobs, last)
        busy = {s for s in picks.values() if s is not None}
        for job in jobs:
            chosen = picks[job.id]
            if chosen is None:
                continue
            for v in job.volunteers:
                if v in busy and v != chosen:
                    continue
                assert rank_key(job, chosen, last) <= rank_key(job, v, last)
        record_picks(last, d, picks)


def test_queue_order_excludes_busy():
    """queue_order skips excluded students but keeps rank order among the rest."""
    job = JobInfo(1, 0, (1, 2, 3))
    last: LastServed = {1: {1: "2026-11-07", 3: "2026-11-08"}}
    assert queue_order(job, last, exclude=frozenset({2})) == [1, 3]
