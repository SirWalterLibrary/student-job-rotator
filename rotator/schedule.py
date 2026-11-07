"""Schedule service: the day walker, freeze step, session views, queue status."""
import sqlite3
from datetime import date

from .dates import (
    class_days,
    first_class_day_on_or_after,
    is_class_day,
    next_class_day_after,
    parse_iso,
)
from .db import get_setting, set_setting, utc_now_iso
from .errors import RotatorError
from .scheduler import JobInfo, LastServed, pick_session, queue_order, record_picks

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_start_date(conn: sqlite3.Connection, today: date) -> date:
    """The start_date setting, stored on first use as the first class day on/after today."""
    raw = get_setting(conn, "start_date")
    if raw is None:
        raw = first_class_day_on_or_after(today).isoformat()
        set_setting(conn, "start_date", raw)
    return parse_iso(raw)


def load_jobs(conn: sqlite3.Connection) -> list[JobInfo]:
    """Active jobs ordered by sort_order, id, with volunteers by joined_at, student_id."""
    jobs = []
    for job in conn.execute("SELECT id, sort_order FROM jobs WHERE active = 1 ORDER BY sort_order, id"):
        vols = conn.execute(
            "SELECT v.student_id FROM volunteers v JOIN students s ON s.id = v.student_id "
            "WHERE v.job_id = ? AND s.active = 1 ORDER BY v.joined_at, v.student_id",
            (job["id"],),
        )
        jobs.append(JobInfo(job["id"], job["sort_order"], tuple(v["student_id"] for v in vols)))
    return jobs


def load_rows(conn: sqlite3.Connection) -> dict[str, dict[int, int]]:
    """All stored assignments keyed by ISO date, then job_id -> student_id."""
    rows: dict[str, dict[int, int]] = {}
    for r in conn.execute("SELECT date, job_id, student_id FROM assignments"):
        rows.setdefault(r["date"], {})[r["job_id"]] = r["student_id"]
    return rows


def cancelled_dates(conn: sqlite3.Connection) -> frozenset[date]:
    """All dates whose session row is cancelled."""
    rows = conn.execute("SELECT date FROM sessions WHERE status = 'cancelled'").fetchall()
    return frozenset(parse_iso(r["date"]) for r in rows)


def _mark_frozen(conn: sqlite3.Connection, d: date) -> None:
    """Insert or update the session row for d, setting frozen = 1."""
    conn.execute(
        "INSERT INTO sessions (date, frozen) VALUES (?, 1) "
        "ON CONFLICT (date) DO UPDATE SET frozen = 1, "
        "status = COALESCE(sessions.status, 'held'), "
        "note = COALESCE(sessions.note, '')",
        (d.isoformat(),),
    )


def _write_picks(conn: sqlite3.Connection, d: date, jobs: list[JobInfo],
                 existing: dict[int, int], picks: dict[int, int | None]) -> None:
    """Insert missing auto rows for a day (stored rows are never changed) and freeze it."""
    job_ids = {j.id for j in jobs}
    for job_id, student_id in picks.items():
        if student_id is None or job_id not in job_ids or job_id in existing:
            continue
        conn.execute(
            "INSERT INTO assignments (date, job_id, student_id, source, note, created_at) "
            "VALUES (?, ?, ?, 'auto', '', ?)",
            (d.isoformat(), job_id, student_id, utc_now_iso()),
        )
    _mark_frozen(conn, d)


def walk(conn: sqlite3.Connection, today: date, last_date: date, write: bool):
    """Visit every class day start..last_date; return (results, final last_served).

    results maps ISO date -> {"status": "cancelled"} or {"picks": {job_id: student_id}}.
    Writes happen only when write is true, only for d <= today, only for days with at
    least one volunteer, and only for rows not already stored.
    """
    jobs = load_jobs(conn)
    stored = load_rows(conn)
    cancelled = cancelled_dates(conn)
    start = get_start_date(conn, today)
    results: dict[str, dict] = {}
    last: LastServed = {}
    for d in class_days(start, last_date):
        if d in cancelled:
            results[d.isoformat()] = {"status": "cancelled"}
            continue
        existing = stored.get(d.isoformat(), {})
        if d < today and conn.execute(
            "SELECT 1 FROM sessions WHERE date = ? AND frozen = 1", (d.isoformat(),)
        ).fetchone() is not None:
            picks = dict(existing)
        else:
            picks = pick_session(jobs, last, locked=existing or None)
        if write and d <= today and any(j.volunteers for j in jobs):
            _write_picks(conn, d, jobs, existing, picks)
        record_picks(last, d.isoformat(), picks)
        results[d.isoformat()] = {"picks": picks}
    conn.commit()
    return results, last


def set_start_date(conn: sqlite3.Connection, today: date, iso_date: str) -> date:
    """Store a new start_date: must be Sat/Sun (400) and not after any frozen session (409)."""
    try:
        d = parse_iso(iso_date)
    except ValueError:
        raise RotatorError("start_date must be YYYY-MM-DD", 400)
    if not is_class_day(d):
        raise RotatorError("start_date must be a Saturday or Sunday", 400)
    if d < today:
        raise RotatorError("start_date must be today or later", 400)
    max_frozen = conn.execute(
        "SELECT MAX(date) FROM sessions WHERE frozen = 1"
    ).fetchone()[0]
    if max_frozen is not None and d > parse_iso(max_frozen):
        raise RotatorError("start_date may not be after a frozen session", 409)
    set_setting(conn, "start_date", d.isoformat())
    return d


def freeze_through(conn: sqlite3.Connection, today: date) -> None:
    """Freeze every class day from the start through today (call at the start of each read)."""
    walk(conn, today, today, write=True)


def build_sessions(conn: sqlite3.Connection, today: date, first: date, last: date) -> list[dict]:
    """Freeze through today, then session views for every class day in first..last."""
    freeze_through(conn, today)
    results, _ = walk(conn, today, last, write=False)
    return [
        session_view(conn, d, today, results[d.isoformat()])
        for d in class_days(first, last)
        if d.isoformat() in results
    ]


def session_view(conn: sqlite3.Connection, d: date, today: date, res: dict) -> dict:
    """One session view in the exact shape of spec 04 for a walked day."""
    srow = conn.execute(
        "SELECT status, note FROM sessions WHERE date = ?", (d.isoformat(),)
    ).fetchone()
    cancelled = srow is not None and srow["status"] == "cancelled"
    roles: list[dict] = []
    if not cancelled:
        stored = {
            r["job_id"]: r
            for r in conn.execute(
                "SELECT a.job_id, a.source, a.note, a.student_id "
                "FROM assignments a WHERE a.date = ?",
                (d.isoformat(),),
            )
        }
        for jrow in conn.execute(
            "SELECT id, name, description, icon FROM jobs WHERE active = 1 "
            "ORDER BY sort_order, id"
        ):
            row = stored.get(jrow["id"])
            if row is not None:
                student_id, source, note, projected = (
                    row["student_id"], row["source"], row["note"], False)
            else:
                student_id = res.get("picks", {}).get(jrow["id"])
                if student_id is None:
                    continue
                source, note, projected = "auto", "", d >= today
            s = conn.execute(
                "SELECT id, name FROM students WHERE id = ?", (student_id,)
            ).fetchone()
            roles.append({
                "job": {"id": jrow["id"], "name": jrow["name"],
                        "description": jrow["description"], "icon": jrow["icon"]},
                "student": {"id": s["id"], "name": s["name"]},
                "source": source, "projected": projected, "note": note,
            })
    return {
        "date": d.isoformat(),
        "weekday": WEEKDAYS[d.weekday()],
        "status": "cancelled" if cancelled else "held",
        "is_today": d == today,
        "is_past": d < today,
        "note": "" if srow is None else srow["note"],
        "roles": roles,
    }


def queue_status(conn: sqlite3.Connection, today: date) -> list[dict]:
    """One queue entry per active job: order, turns, last_served, single_volunteer flag."""
    jobs = load_jobs(conn)
    n = next_class_day_after(today, cancelled_dates(conn))
    _, last = walk(conn, today, n, write=False)
    out = []
    for job in jobs:
        queue = []
        for sid in queue_order(job, last):
            cnt = conn.execute(
                "SELECT COUNT(*) FROM assignments WHERE job_id = ? AND student_id = ?",
                (job.id, sid),
            ).fetchone()[0]
            name = conn.execute(
                "SELECT name FROM students WHERE id = ?", (sid,)
            ).fetchone()["name"]
            queue.append({
                "student": {"id": sid, "name": name},
                "turns": cnt,
                "last_served": last.get(job.id, {}).get(sid),
            })
        out.append({
            "job": {"id": job.id, "name": conn.execute(
                "SELECT name FROM jobs WHERE id = ?", (job.id,)
            ).fetchone()["name"]},
            "volunteer_count": len(job.volunteers),
            "single_volunteer": len(job.volunteers) == 1,
            "queue": queue,
        })
    return out
