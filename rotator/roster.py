"""Roster management over SQLite: students, jobs, volunteers (no Flask)."""
import sqlite3
from datetime import date

from .db import utc_now_iso
from .errors import RotatorError


def _clean(text: str, field: str, min_len: int, max_len: int) -> str:
    """Trim a text field and enforce its length bounds (400 on failure)."""
    value = (text or "").strip()
    if not min_len <= len(value) <= max_len:
        raise RotatorError(f"{field} must be {min_len} to {max_len} characters.", 400)
    return value


def student_view(conn: sqlite3.Connection, student_id: int) -> dict:
    """Return the API view of one student (404 if missing)."""
    row = conn.execute("SELECT id, name, active FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        raise RotatorError("Student not found.", 404)
    return {"id": row["id"], "name": row["name"], "active": bool(row["active"])}


def list_students(conn: sqlite3.Connection, include_archived: bool = False) -> list[dict]:
    """All (or only active) students ordered by name, case-insensitive."""
    where = "" if include_archived else " WHERE active = 1"
    rows = conn.execute(
        f"SELECT id, name, active FROM students{where} ORDER BY name COLLATE NOCASE, id"
    )
    return [{"id": r["id"], "name": r["name"], "active": bool(r["active"])} for r in rows]


def add_student(conn: sqlite3.Connection, name: str) -> tuple[dict, bool]:
    """Insert a student; re-activate an archived twin. Returns (view, reactivated)."""
    name = _clean(name, "Name", 1, 40)
    row = conn.execute("SELECT id, active FROM students WHERE name = ?", (name,)).fetchone()
    if row is not None:
        if row["active"]:
            raise RotatorError("A student with this name already exists.", 409)
        conn.execute("UPDATE students SET active = 1 WHERE id = ?", (row["id"],))
        conn.commit()
        return student_view(conn, row["id"]), True
    cur = conn.execute(
        "INSERT INTO students (name, active, created_at) VALUES (?, 1, ?)",
        (name, utc_now_iso()),
    )
    conn.commit()
    return student_view(conn, cur.lastrowid), False


def rename_student(conn: sqlite3.Connection, student_id: int, name: str) -> dict:
    """Rename a student (404 if missing, 409 on a case-insensitive clash)."""
    if conn.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone() is None:
        raise RotatorError("Student not found.", 404)
    name = _clean(name, "Name", 1, 40)
    try:
        conn.execute("UPDATE students SET name = ? WHERE id = ?", (name, student_id))
        conn.commit()
    except sqlite3.IntegrityError:
        raise RotatorError("A student with this name already exists.", 409)
    return student_view(conn, student_id)


def archive_student(conn: sqlite3.Connection, student_id: int, today: date) -> None:
    """Deactivate a student, removing their volunteer rows and future assignments."""
    if conn.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone() is None:
        raise RotatorError("Student not found.", 404)
    today_iso = today.isoformat()
    conn.execute("UPDATE students SET active = 0 WHERE id = ?", (student_id,))
    conn.execute("DELETE FROM volunteers WHERE student_id = ?", (student_id,))
    conn.execute(
        "DELETE FROM assignments WHERE student_id = ? AND date > ?",
        (student_id, today_iso),
    )
    conn.commit()


def _job_view(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    """Render a jobs row with active volunteer ids ordered by joined_at, student_id."""
    vols = conn.execute(
        "SELECT v.student_id FROM volunteers v JOIN students s ON s.id = v.student_id "
        "WHERE v.job_id = ? AND s.active = 1 ORDER BY v.joined_at, v.student_id",
        (row["id"],),
    )
    return {
        "id": row["id"], "name": row["name"], "description": row["description"],
        "icon": row["icon"], "sort_order": row["sort_order"], "active": bool(row["active"]),
        "volunteer_ids": [r["student_id"] for r in vols],
    }


def job_view(conn: sqlite3.Connection, job_id: int) -> dict:
    """Return the API view of one job with volunteer_ids (404 if missing)."""
    row = conn.execute(
        "SELECT id, name, description, icon, sort_order, active FROM jobs WHERE id = ?",
        (job_id,),
    ).fetchone()
    if row is None:
        raise RotatorError("Job not found.", 404)
    return _job_view(conn, row)


def list_jobs(conn: sqlite3.Connection, include_archived: bool = False) -> list[dict]:
    """All (or only active) jobs ordered by sort_order, id, with volunteer_ids."""
    where = "" if include_archived else " WHERE active = 1"
    rows = conn.execute(
        f"SELECT id, name, description, icon, sort_order, active FROM jobs{where} "
        "ORDER BY sort_order, id"
    )
    return [_job_view(conn, r) for r in rows]


def set_volunteers(conn: sqlite3.Connection, job_id: int, student_ids: list[int]) -> dict:
    """Replace a job's volunteer set; existing keep joined_at, new get fresh ones."""
    if conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone() is None:
        raise RotatorError("Job not found.", 404)
    if len(set(student_ids)) != len(student_ids):
        raise RotatorError("Duplicate student ids.", 400)
    for sid in student_ids:
        s = conn.execute("SELECT active FROM students WHERE id = ?", (sid,)).fetchone()
        if s is None or not s["active"]:
            raise RotatorError("Student not found or archived.", 400)
    existing = {
        r["student_id"]: r["joined_at"]
        for r in conn.execute(
            "SELECT student_id, joined_at FROM volunteers WHERE job_id = ?", (job_id,)
        )
    }
    conn.execute("DELETE FROM volunteers WHERE job_id = ?", (job_id,))
    for sid in student_ids:
        conn.execute(
            "INSERT INTO volunteers (job_id, student_id, joined_at) VALUES (?, ?, ?)",
            (job_id, sid, existing.get(sid) or utc_now_iso()),
        )
    conn.commit()
    return job_view(conn, job_id)


def add_job(conn: sqlite3.Connection, name: str, description: str = "", icon: str = "",
            volunteer_ids: list[int] | None = None) -> tuple[dict, bool]:
    """Create a job (or re-activate an archived twin); returns (view, reactivated)."""
    name = _clean(name, "Name", 1, 60)
    description = (description or "").strip()
    icon = (icon or "").strip()
    if len(description) > 200:
        raise RotatorError("Description must be at most 200 characters.", 400)
    if len(icon) > 8:
        raise RotatorError("Icon must be at most 8 characters.", 400)
    volunteer_ids = volunteer_ids or []
    existing = conn.execute("SELECT id, active FROM jobs WHERE name = ?", (name,)).fetchone()
    if existing is not None:
        if existing["active"]:
            raise RotatorError("A job with this name already exists.", 409)
        conn.execute("UPDATE jobs SET active = 1 WHERE id = ?", (existing["id"],))
        conn.commit()
        if volunteer_ids:
            set_volunteers(conn, existing["id"], volunteer_ids)
        return job_view(conn, existing["id"]), True
    max_order = conn.execute("SELECT COALESCE(MAX(sort_order), -1) FROM jobs").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO jobs (name, description, icon, sort_order, active, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?)",
        (name, description, icon, max_order + 1, utc_now_iso()),
    )
    conn.commit()
    if volunteer_ids:
        set_volunteers(conn, cur.lastrowid, volunteer_ids)
    return job_view(conn, cur.lastrowid), False


def update_job(conn: sqlite3.Connection, job_id: int, name: str | None = None,
               description: str | None = None, icon: str | None = None) -> dict:
    """Update any of name/description/icon on an existing job (404 if missing)."""
    row = conn.execute(
        "SELECT id, name, description, icon FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()
    if row is None:
        raise RotatorError("Job not found.", 404)
    if name is not None:
        name = _clean(name, "Name", 1, 60)
        if conn.execute(
            "SELECT 1 FROM jobs WHERE name = ? AND id != ?", (name, job_id)
        ).fetchone() is not None:
            raise RotatorError("A job with this name already exists.", 409)
    if description is not None and len(description.strip()) > 200:
        raise RotatorError("Description must be at most 200 characters.", 400)
    if icon is not None and len(icon.strip()) > 8:
        raise RotatorError("Icon must be at most 8 characters.", 400)
    conn.execute(
        "UPDATE jobs SET name = COALESCE(?, name), description = COALESCE(?, description), "
        "icon = COALESCE(?, icon) WHERE id = ?",
        (name, None if description is None else description.strip(),
         None if icon is None else icon.strip(), job_id),
    )
    conn.commit()
    return job_view(conn, job_id)


def archive_job(conn: sqlite3.Connection, job_id: int, today: date) -> None:
    """Deactivate a job, deleting its future assignments (volunteers are kept)."""
    if conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone() is None:
        raise RotatorError("Job not found.", 404)
    conn.execute("UPDATE jobs SET active = 0 WHERE id = ?", (job_id,))
    conn.execute(
        "DELETE FROM assignments WHERE job_id = ? AND date > ?",
        (job_id, today.isoformat()),
    )
    conn.commit()


def reorder_jobs(conn: sqlite3.Connection, ids: list) -> None:
    """Set sort_order 0..n-1 in the given order; ids must be exactly the active ids."""
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise RotatorError("ids must be a list of job ids.", 400)
    active = {r["id"] for r in conn.execute("SELECT id FROM jobs WHERE active = 1")}
    if set(ids) != active or len(set(ids)) != len(ids):
        raise RotatorError("ids must be exactly the active job ids.", 400)
    for order, job_id in enumerate(ids):
        conn.execute("UPDATE jobs SET sort_order = ? WHERE id = ?", (order, job_id))
    conn.commit()
