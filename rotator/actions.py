"""Session actions: absent swap, cancel/restore, manual override, clearing."""
import sqlite3
import uuid
from datetime import date

from .dates import is_class_day, next_class_day_after, parse_iso
from .db import utc_now_iso
from .errors import RotatorError
from .schedule import build_sessions, cancelled_dates, freeze_through, load_jobs
from .scheduler import queue_order


def _check_date(conn: sqlite3.Connection, today: date, iso_date: str) -> date:
    """Parse an action date; 400 unless it is a Saturday/Sunday on or after today."""
    try:
        d = parse_iso(iso_date)
    except (ValueError, TypeError):
        raise RotatorError("date must be YYYY-MM-DD", 400)
    if d < today or not is_class_day(d):
        raise RotatorError("date must be a Saturday or Sunday on or after today", 400)
    return d


def _active_job(conn: sqlite3.Connection, job_id: int):
    """The JobInfo for job_id, or RotatorError 404 if it is missing/inactive."""
    job = next((j for j in load_jobs(conn) if j.id == job_id), None)
    if job is None:
        raise RotatorError("Unknown or inactive job", 404)
    return job


def _student_name(conn: sqlite3.Connection, student_id: int) -> str:
    """The name of a student id."""
    return conn.execute(
        "SELECT name FROM students WHERE id = ?", (student_id,)
    ).fetchone()["name"]


def swap_absent(conn: sqlite3.Connection, today: date, iso_date: str, job_id: int,
                partner_id: int | None = None, vacant: bool = False) -> dict:
    """Swap an absent student's role with a partner and book the absent student's make-up turn."""
    d = _check_date(conn, today, iso_date)
    freeze_through(conn, today)
    session = build_sessions(conn, today, d, d)[0]
    if session["status"] == "cancelled":
        raise RotatorError("Cannot swap on a cancelled day", 409)
    roles = {r["job"]["id"]: r for r in session["roles"]}
    a = (roles.get(job_id) or {}).get("student")
    if a is None:
        raise RotatorError("Nobody holds that job on that day", 404)
    if vacant:
        with conn:
            conn.execute(
                "DELETE FROM assignments WHERE date = ? AND job_id = ?",
                (d.isoformat(), job_id))
        # Return the pre-delete view minus the role: re-walking would let the
        # walker re-fill the slot we just emptied (see NOTES.md).
        view = dict(session)
        view["roles"] = [r for r in session["roles"] if r["job"]["id"] != job_id]
        return view
    job = _active_job(conn, job_id)
    n = next_class_day_after(d, cancelled_dates(conn))
    next_session = build_sessions(conn, today, n, n)[0]
    c = ({r["job"]["id"]: r for r in next_session["roles"]}.get(job_id) or {}).get("student")
    a_id = a["id"]
    busy = {r["student"]["id"] for r in session["roles"]}
    if partner_id is not None:
        if partner_id == a_id:
            raise RotatorError("Partner must be a different student", 409)
        if partner_id not in job.volunteers:
            raise RotatorError("Partner must be an active volunteer of the job", 409)
        if partner_id in busy:
            raise RotatorError("Partner already has a role that day", 409)
        b = partner_id
    else:
        if c is not None and c["id"] != a_id and c["id"] not in busy:
            b = c["id"]
        else:
            order = queue_order(job, {}, exclude=frozenset((a_id,)) | busy)
            if not order:
                raise RotatorError("No available partner. Leave the job empty instead?", 409)
            b = order[0]
    if any(r["student"]["id"] == a_id for r in next_session["roles"]):
        raise RotatorError("The absent student already has a role on the next class day", 409)
    row = conn.execute(
        "SELECT source FROM assignments WHERE date = ? AND job_id = ?",
        (n.isoformat(), job_id)).fetchone()
    if row is not None and row["source"] in ("swap", "manual"):
        raise RotatorError("A swap or manual assignment already occupies that slot", 409)
    group_id = uuid.uuid4().hex
    with conn:
        cur = conn.execute(
            "SELECT id FROM assignments WHERE date = ? AND job_id = ?",
            (d.isoformat(), job_id)).fetchone()
        if cur is not None:
            conn.execute(
                "UPDATE assignments SET student_id = ?, source = 'swap', "
                "note = ?, group_id = ? WHERE id = ?",
                (b, f"Covering for {a['name']} (absent)", group_id, cur["id"]))
        else:
            conn.execute(
                "INSERT INTO assignments (date, job_id, student_id, source, note, "
                "group_id, created_at) VALUES (?, ?, ?, 'swap', ?, ?, ?)",
                (d.isoformat(), job_id, b,
                 f"Covering for {a['name']} (absent)", group_id, utc_now_iso()))
        conn.execute(
            "DELETE FROM assignments WHERE date = ? AND job_id = ?",
            (n.isoformat(), job_id))
        conn.execute(
            "INSERT INTO assignments (date, job_id, student_id, source, note, "
            "group_id, created_at) VALUES (?, ?, ?, 'swap', ?, ?, ?)",
            (n.isoformat(), job_id, a_id,
             f"Make-up turn for {a['name']} (absent on {d.isoformat()})",
             group_id, utc_now_iso()))
    return {
        "date": d.isoformat(),
        "next_date": n.isoformat(),
        "covering": {"id": b, "name": _student_name(conn, b)},
        "absent": a,
    }


def cancel_session(conn: sqlite3.Connection, today: date, iso_date: str,
                   note: str = "") -> None:
    """Cancel a class day: delete its assignments and the other rows of any swap groups."""
    if not isinstance(note, str):
        raise RotatorError("note must be a string", 400)
    d = _check_date(conn, today, iso_date)
    freeze_through(conn, today)
    status = conn.execute(
        "SELECT status FROM sessions WHERE date = ?", (d.isoformat(),)
    ).fetchone()
    if status is not None and status["status"] == "cancelled":
        raise RotatorError("Session is already cancelled", 409)
    with conn:
        conn.execute(
            "INSERT INTO sessions (date, status, note) VALUES (?, 'cancelled', ?) "
            "ON CONFLICT (date) DO UPDATE SET status = 'cancelled', note = ?",
            (d.isoformat(), note, note))
        rows = conn.execute(
            "SELECT group_id FROM assignments WHERE date = ?", (d.isoformat(),)
        ).fetchall()
        conn.execute("DELETE FROM assignments WHERE date = ?", (d.isoformat(),))
        for r in rows:
            if r["group_id"] is not None:
                conn.execute(
                    "DELETE FROM assignments WHERE group_id = ? AND date != ?",
                    (r["group_id"], d.isoformat()))


def restore_session(conn: sqlite3.Connection, today: date, iso_date: str) -> None:
    """Restore a cancelled day to held; the next read re-fills the day if it is today."""
    d = _check_date(conn, today, iso_date)
    freeze_through(conn, today)
    status = conn.execute(
        "SELECT status FROM sessions WHERE date = ?", (d.isoformat(),)
    ).fetchone()
    if status is None or status["status"] != "cancelled":
        raise RotatorError("Session is not cancelled", 409)
    with conn:
        conn.execute(
            "INSERT INTO sessions (date, status, note) VALUES (?, 'held', '') "
            "ON CONFLICT (date) DO UPDATE SET status = 'held', note = ''",
            (d.isoformat(),))


def set_manual(conn: sqlite3.Connection, today: date, iso_date: str,
               job_id: int, student_id: int) -> None:
    """Teacher override: put a volunteer on a job for a held day, replacing any row there."""
    d = _check_date(conn, today, iso_date)
    freeze_through(conn, today)
    session = build_sessions(conn, today, d, d)[0]
    if session["status"] == "cancelled":
        raise RotatorError("Day is cancelled; restore it first", 409)
    if not isinstance(student_id, int):
        raise RotatorError("student_id must be an id", 400)
    job = _active_job(conn, job_id)
    if student_id not in job.volunteers:
        raise RotatorError("Student must be an active volunteer of the job", 400)
    if any(r["student"]["id"] == student_id and r["job"]["id"] != job_id
            for r in session["roles"]):
        raise RotatorError("Student already has a role that day", 409)
    old_group = conn.execute(
        "SELECT group_id FROM assignments WHERE date = ? AND job_id = ?",
        (d.isoformat(), job_id)).fetchone()
    old_group = old_group["group_id"] if old_group is not None else None
    with conn:
        conn.execute(
            "DELETE FROM assignments WHERE date = ? AND job_id = ?",
            (d.isoformat(), job_id))
        if old_group is not None:
            conn.execute("DELETE FROM assignments WHERE group_id = ?", (old_group,))
        conn.execute(
            "INSERT INTO assignments (date, job_id, student_id, source, note, created_at) "
            "VALUES (?, ?, ?, 'manual', '', ?)",
            (d.isoformat(), job_id, student_id, utc_now_iso()))


def clear_assignment(conn: sqlite3.Connection, today: date, iso_date: str,
                     job_id: int) -> dict:
    """Delete the stored row for a slot and the other rows of its swap group; return the view."""
    d = _check_date(conn, today, iso_date)
    freeze_through(conn, today)
    session = build_sessions(conn, today, d, d)[0]
    row = conn.execute(
        "SELECT group_id FROM assignments WHERE date = ? AND job_id = ?",
        (d.isoformat(), job_id)).fetchone()
    if row is None:
        raise RotatorError("No assignment to clear on that day", 404)
    with conn:
        conn.execute(
            "DELETE FROM assignments WHERE date = ? AND job_id = ?",
            (d.isoformat(), job_id))
        if row["group_id"] is not None:
            conn.execute("DELETE FROM assignments WHERE group_id = ?", (row["group_id"],))
    # Same as vacant: do not re-walk, or the walker re-fills the cleared slot (NOTES.md).
    view = dict(session)
    view["roles"] = [r for r in session["roles"] if r["job"]["id"] != job_id]
    return view
