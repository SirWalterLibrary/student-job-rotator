"""Tests for the database schema and helpers."""
import sqlite3

import pytest

from rotator.db import connect, init_db, get_setting, set_setting, utc_now_iso


@pytest.fixture
def db(tmp_path):
    """An initialized roster database in a temp directory."""
    conn = connect(str(tmp_path / "rotator.db"))
    init_db(conn)
    yield conn
    conn.close()


def _student(conn, name: str) -> int:
    """Insert a student and return its id."""
    cur = conn.execute(
        "INSERT INTO students (name, active, created_at) VALUES (?, 1, ?)",
        (name, utc_now_iso()),
    )
    conn.commit()
    return cur.lastrowid


def _job(conn, name: str) -> int:
    """Insert a job and return its id."""
    cur = conn.execute(
        "INSERT INTO jobs (name, description, icon, sort_order, active, created_at) "
        "VALUES (?, '', '', 0, 1, ?)",
        (name, utc_now_iso()),
    )
    conn.commit()
    return cur.lastrowid


def test_schema_creates_all_tables(db):
    """init_db creates all six roster tables."""
    names = {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"students", "jobs", "volunteers", "sessions", "assignments", "settings"} <= names


def test_init_db_is_idempotent(db):
    """Calling init_db twice changes nothing and does not error."""
    init_db(db)
    init_db(db)
    names = {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "students" in names


def test_foreign_keys_enforced(db):
    """A volunteer referencing a missing job raises IntegrityError."""
    _student(db, "Yusuf")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO volunteers (job_id, student_id, joined_at) VALUES (?, ?, ?)",
            (999, 1, utc_now_iso()),
        )


def test_unique_student_per_day(db):
    """One student cannot hold two jobs on the same date."""
    sid = _student(db, "Yusuf")
    j1 = _job(db, "Mu'adhin")
    j2 = _job(db, "Cleaner")
    db.execute(
        "INSERT INTO assignments (date, job_id, student_id, source, note, created_at) "
        "VALUES (?, ?, ?, 'auto', '', ?)",
        ("2026-11-07", j1, sid, utc_now_iso()),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO assignments (date, job_id, student_id, source, note, created_at) "
            "VALUES (?, ?, ?, 'auto', '', ?)",
            ("2026-11-07", j2, sid, utc_now_iso()),
        )


def test_unique_job_per_day(db):
    """One job cannot be assigned to two students on the same date."""
    s1 = _student(db, "Yusuf")
    s2 = _student(db, "Maryam")
    j1 = _job(db, "Mu'adhin")
    db.execute(
        "INSERT INTO assignments (date, job_id, student_id, source, note, created_at) "
        "VALUES (?, ?, ?, 'auto', '', ?)",
        ("2026-11-07", j1, s1, utc_now_iso()),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO assignments (date, job_id, student_id, source, note, created_at) "
            "VALUES (?, ?, ?, 'auto', '', ?)",
            ("2026-11-07", j1, s2, utc_now_iso()),
        )


def test_names_unique_case_insensitive(db):
    """Student names are unique ignoring case."""
    _student(db, "Yusuf")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO students (name, active, created_at) VALUES (?, 1, ?)",
            ("yusuf", utc_now_iso()),
        )


def test_settings_roundtrip(db):
    """get_setting returns the default until set, then the latest value."""
    assert get_setting(db, "start_date") is None
    assert get_setting(db, "start_date", "2026-11-07") == "2026-11-07"
    set_setting(db, "start_date", "2026-11-07")
    assert get_setting(db, "start_date") == "2026-11-07"
    set_setting(db, "start_date", "2026-11-08")
    assert get_setting(db, "start_date") == "2026-11-08"
    count = db.execute("SELECT COUNT(*) FROM settings WHERE key = 'start_date'").fetchone()[0]
    assert count == 1


def test_data_persists_between_connections(tmp_path):
    """Rows written on one connection are visible after reopening the file."""
    path = str(tmp_path / "rotator.db")
    conn = connect(path)
    init_db(conn)
    conn.execute(
        "INSERT INTO students (name, active, created_at) VALUES (?, 1, ?)",
        ("Yusuf", utc_now_iso()),
    )
    conn.commit()
    conn.close()

    reopened = connect(path)
    try:
        row = reopened.execute("SELECT name FROM students").fetchone()
        assert row["name"] == "Yusuf"
    finally:
        reopened.close()
