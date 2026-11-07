"""Tests for the schedule service (walker, freeze, session views, queue status)."""
from datetime import date

import pytest

from rotator.db import connect, init_db, set_setting
from rotator.schedule import (
    build_sessions,
    cancelled_dates,
    freeze_through,
    get_start_date,
    queue_status,
    walk,
)

from tests.helpers import make_job, make_students

SAT = date(2026, 11, 7)


@pytest.fixture
def conn(tmp_path):
    """A fresh roster database connection."""
    c = connect(str(tmp_path / "rotator.db"))
    init_db(c)
    yield c
    c.close()


def _names(session: dict) -> list[str]:
    """Student names of a session view's roles, in role order."""
    return [r["student"]["name"] for r in session["roles"]]


def test_first_freeze_writes_one_auto_row_per_job(conn):
    """Freezing a Saturday stores one auto row per job; a second freeze changes nothing."""
    a, b = make_students(conn, ("A", "B"))
    j1 = make_job(conn, "Mu'adhin", [a])
    j2 = make_job(conn, "Cleaner", [b])
    freeze_through(conn, SAT)
    rows = conn.execute("SELECT date, job_id, student_id, source FROM assignments ORDER BY job_id").fetchall()
    assert [(r["date"], r["job_id"], r["student_id"], r["source"]) for r in rows] == [
        ("2026-11-07", j1, a, "auto"), ("2026-11-07", j2, b, "auto")]
    srow = conn.execute("SELECT status, frozen FROM sessions WHERE date = '2026-11-07'").fetchone()
    assert (srow["status"], srow["frozen"]) == ("held", 1)
    before = {(r["job_id"], r["student_id"]) for r in rows}
    freeze_through(conn, SAT)
    after = {(r["job_id"], r["student_id"])
             for r in conn.execute("SELECT job_id, student_id FROM assignments")}
    assert after == before
    assert conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 2


def test_friday_view_projects_and_stores_nothing(conn):
    """A Friday's view projects Sat/Sun; nothing is stored for them."""
    a, b, c = make_students(conn, ("A", "B", "C"))
    make_job(conn, "Mu'adhin", [a, b, c])
    set_setting(conn, "start_date", "2026-11-07")
    friday = date(2026, 11, 6)
    sessions = build_sessions(conn, friday, date(2026, 11, 1), date(2026, 11, 30))
    assert [(s["date"], s["weekday"], s["status"], s["is_today"]) for s in sessions[:2]] == [
        ("2026-11-07", "Saturday", "held", False),
        ("2026-11-08", "Sunday", "held", False)]
    assert all(r["projected"] is True for s in sessions for r in s["roles"])
    assert conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_multi_job_roster_never_two_roles_same_day(conn):
    """Over 12 weekends, no student holds two roles on the same day."""
    make_students(conn, ("S1", "S2", "S3", "S4", "S5", "S6", "S7"))
    make_job(conn, "J1", [1, 2, 3, 4])
    make_job(conn, "J2", [2, 3, 5])
    make_job(conn, "J3", [1, 5, 6, 7])
    make_job(conn, "J4", [3])
    set_setting(conn, "start_date", "2026-11-07")
    last_sunday = date(2027, 1, 24)
    sessions = build_sessions(conn, last_sunday, date(2026, 11, 7), last_sunday)
    assert len(sessions) == 24
    for s in sessions:
        ids = [r["student"]["id"] for r in s["roles"]]
        assert len(ids) == 4, s["date"]
        assert len(set(ids)) == 4, s["date"]


def test_single_job_rotates_in_order(conn):
    """A 3-person single job rotates A, B, C, A, B, C... across consecutive class days."""
    a, b, c = make_students(conn, ("A", "B", "C"))
    make_job(conn, "Mu'adhin", [a, b, c])
    set_setting(conn, "start_date", "2026-11-07")
    today = date(2026, 12, 13)   # 12 class days from 2026-11-07
    sessions = build_sessions(conn, today, date(2026, 11, 7), today)
    assert [_names(s)[0] for s in sessions] == \
        ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"]


def test_add_volunteer_changes_next_saturday_not_past(conn):
    """A volunteer added on a weekday is first next Saturday; frozen days are untouched."""
    a, b, c = make_students(conn, ("A", "B", "C"))
    jid = make_job(conn, "Mu'adhin", [a, b])
    set_setting(conn, "start_date", "2026-11-07")
    sunday = date(2026, 11, 8)
    freeze_through(conn, sunday)
    before = {tuple(r) for r in conn.execute(
        "SELECT date, job_id, student_id, source FROM assignments")}
    conn.execute(
        "INSERT INTO volunteers (job_id, student_id, joined_at) VALUES (?, ?, '2026-11-08T12:00:00+00:00')",
        (jid, c))
    conn.commit()
    results, _ = walk(conn, sunday, date(2026, 11, 14), write=False)
    assert results["2026-11-14"]["picks"][jid] == c
    assert results["2026-11-07"]["picks"][jid] == a
    assert results["2026-11-08"]["picks"][jid] == b
    after = {tuple(r) for r in conn.execute(
        "SELECT date, job_id, student_id, source FROM assignments")}
    assert after == before


def test_missed_weeks_frozen_in_order(conn):
    """First use on 2026-11-22 freezes 11-07, 08, 14, 15, 21 in order, then 11-22."""
    a, b, c = make_students(conn, ("A", "B", "C"))
    jid = make_job(conn, "Mu'adhin", [a, b, c])
    set_setting(conn, "start_date", "2026-11-07")
    freeze_through(conn, date(2026, 11, 22))
    srows = conn.execute(
        "SELECT date, frozen, status FROM sessions ORDER BY date").fetchall()
    assert [r["date"] for r in srows] == [
        "2026-11-07", "2026-11-08", "2026-11-14", "2026-11-15", "2026-11-21", "2026-11-22"]
    assert all(r["frozen"] == 1 and r["status"] == "held" for r in srows)
    picks = {r["date"]: r["student_id"]
             for r in conn.execute("SELECT date, student_id FROM assignments")}
    assert picks == {
        "2026-11-07": a, "2026-11-08": b, "2026-11-14": c,
        "2026-11-15": a, "2026-11-21": b, "2026-11-22": c}


def test_queue_status_order_turns_last_served(conn):
    """queue_status orders by next-in-line, with turns, last_served, single flag."""
    a, b, c = make_students(conn, ("A", "B", "C"))
    jid = make_job(conn, "Mu'adhin", [a, b, c])
    set_setting(conn, "start_date", "2026-11-07")
    sunday = date(2026, 11, 8)
    freeze_through(conn, sunday)
    status = {item["job"]["id"]: item for item in queue_status(conn, sunday)}
    item = status[jid]
    assert item["volunteer_count"] == 3
    assert item["single_volunteer"] is False
    assert [(q["student"]["id"], q["turns"], q["last_served"]) for q in item["queue"]] == [
        (a, 1, "2026-11-07"), (b, 1, "2026-11-08"), (c, 0, "2026-11-14")]


def test_queue_status_flags_single_volunteer(conn):
    """A job with exactly one volunteer is flagged single_volunteer."""
    a = make_students(conn, ("A",))[0]
    jid = make_job(conn, "Mu'adhin", [a])
    status = {item["job"]["id"]: item for item in queue_status(conn, SAT)}
    assert status[jid]["single_volunteer"] is True
    assert status[jid]["volunteer_count"] == 1


def test_cancelled_day_skipped_consumes_no_turns(conn):
    """A cancelled day is skipped by walk and consumes no turns."""
    a, b = make_students(conn, ("A", "B"))
    jid = make_job(conn, "Mu'adhin", [a, b])
    set_setting(conn, "start_date", "2026-11-07")
    conn.execute(
        "INSERT INTO sessions (date, status, note) VALUES ('2026-11-07', 'cancelled', 'Away')")
    conn.commit()
    assert date(2026, 11, 7) in cancelled_dates(conn)
    freeze_through(conn, date(2026, 11, 8))
    assert conn.execute(
        "SELECT COUNT(*) FROM assignments WHERE date = '2026-11-07'").fetchone()[0] == 0
    results, _ = walk(conn, date(2026, 11, 8), date(2026, 11, 15), write=False)
    assert results["2026-11-07"] == {"status": "cancelled"}
    assert results["2026-11-08"]["picks"][jid] == a
    assert results["2026-11-14"]["picks"][jid] == b
    assert results["2026-11-15"]["picks"][jid] == a


def test_job_added_later_today_fills_frozen_session(conn):
    """A job added later today gets an auto row; existing rows are unchanged."""
    a, b = make_students(conn, ("A", "B"))
    j1 = make_job(conn, "Mu'adhin", [a])
    freeze_through(conn, SAT)
    j2 = make_job(conn, "Cleaner", [b])
    freeze_through(conn, SAT)
    rows = {(r["job_id"], r["student_id"], r["source"])
            for r in conn.execute("SELECT job_id, student_id, source FROM assignments")}
    assert rows == {(j1, a, "auto"), (j2, b, "auto")}
