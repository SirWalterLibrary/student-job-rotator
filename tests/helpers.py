"""Helpers to seed a roster directly in a test database connection."""
from rotator.db import utc_now_iso


def make_students(conn, names) -> list[int]:
    """Insert active students (names in order) and return their ids."""
    ids = []
    for name in names:
        cur = conn.execute(
            "INSERT INTO students (name, active, created_at) VALUES (?, 1, ?)",
            (name, utc_now_iso()),
        )
        ids.append(cur.lastrowid)
    conn.commit()
    return ids


def make_job(conn, name, student_ids=None, description: str = "", icon: str = "") -> int:
    """Insert an active job (next sort_order) with volunteers; return its id."""
    max_order = conn.execute("SELECT COALESCE(MAX(sort_order), -1) FROM jobs").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO jobs (name, description, icon, sort_order, active, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?)",
        (name, description, icon, max_order + 1, utc_now_iso()),
    )
    job_id = cur.lastrowid
    for sid in student_ids or []:
        conn.execute(
            "INSERT INTO volunteers (job_id, student_id, joined_at) VALUES (?, ?, ?)",
            (job_id, sid, utc_now_iso()),
        )
    conn.commit()
    return job_id
