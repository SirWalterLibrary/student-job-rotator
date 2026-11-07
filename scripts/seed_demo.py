"""Seed a Khidmah Roster database with fake demo data (never real students).

Usage:
    python scripts/seed_demo.py --data ./data [--reset]

With --reset every table is emptied first, then the full demo roster is
inserted. Without it, existing rows are kept and names are matched
case-insensitively, so re-running the script is safe. The volunteer order
within each job is the order volunteers will be picked in on a fresh start.
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rotator.db import connect, init_db, set_setting, utc_now_iso  # noqa: E402

START_DATE = "2026-11-07"  # a Saturday, the demo roster's first class day

STUDENTS = [
    "Yusuf", "Maryam", "Ibrahim", "Aisha", "Omar",
    "Fatima", "Hamza", "Khadija", "Bilal", "Zainab",
]

# (name, icon, volunteer names in intended rotation order) — deliberately overlapping.
JOBS = [
    ("Mu'adhin", "\U0001f54c", ["Yusuf", "Omar", "Hamza", "Bilal"]),
    ("Qur'an recitation", "\U0001f4d6", ["Maryam", "Aisha", "Khadija", "Fatima", "Zainab"]),
    ("Du'a leader", "\U0001f90e", ["Ibrahim", "Yusuf", "Maryam", "Bilal"]),
    ("Board cleaner", "\U0001f9fd", ["Omar", "Fatima", "Hamza"]),
    ("Line leader", "\U0001f6b6", ["Aisha", "Ibrahim", "Zainab", "Khadija"]),
    ("Shoe rack helper", "\U0001f45f", ["Hamza", "Fatima", "Bilal", "Zainab", "Omar"]),
]

_TABLES = ("assignments", "sessions", "volunteers", "jobs", "students", "settings")


def _upsert_student(conn, name: str) -> int:
    """Insert the student (or re-use / re-activate the same-named row)."""
    row = conn.execute("SELECT id, active FROM students WHERE name = ?", (name,)).fetchone()
    if row is None:
        cur = conn.execute(
            "INSERT INTO students (name, active, created_at) VALUES (?, 1, ?)",
            (name, utc_now_iso()))
        return cur.lastrowid
    if not row["active"]:
        conn.execute("UPDATE students SET active = 1 WHERE id = ?", (row["id"],))
    return row["id"]


def _upsert_job(conn, name: str, icon: str, sort_order: int) -> int:
    """Insert the job (or re-use / re-activate the same-named row)."""
    row = conn.execute("SELECT id, active FROM jobs WHERE name = ?", (name,)).fetchone()
    if row is None:
        cur = conn.execute(
            "INSERT INTO jobs (name, description, icon, sort_order, active, created_at) "
            "VALUES (?, '', ?, ?, 1, ?)",
            (name, icon, sort_order, utc_now_iso()))
        return cur.lastrowid
    conn.execute(
        "UPDATE jobs SET icon = ?, sort_order = ?, active = 1 WHERE id = ?",
        (icon, sort_order, row["id"]))
    return row["id"]


def seed(conn, reset: bool = False) -> None:
    """Insert the demo roster: 10 students, 6 jobs, overlapping volunteers."""
    if reset:
        for table in _TABLES:
            conn.execute(f"DELETE FROM {table}")
    conn.commit()
    base = datetime.now(timezone.utc)

    def stamp(offset: int) -> str:
        """A distinct ISO timestamp: the volunteer order comes from these."""
        return (base + timedelta(microseconds=offset)).isoformat()

    student_ids = {}
    for i, name in enumerate(STUDENTS):
        student_ids[name] = _upsert_student(conn, name)
    for order, (name, icon, vol_names) in enumerate(JOBS):
        job_id = _upsert_job(conn, name, icon, order)
        conn.execute("DELETE FROM volunteers WHERE job_id = ?", (job_id,))
        for j, vol in enumerate(vol_names):
            conn.execute(
                "INSERT INTO volunteers (job_id, student_id, joined_at) VALUES (?, ?, ?)",
                (job_id, student_ids[vol], stamp(order * 100 + j)))
    set_setting(conn, "start_date", START_DATE)
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Khidmah Roster with demo data.")
    parser.add_argument("--data", default="./data", help="data directory (default ./data)")
    parser.add_argument("--reset", action="store_true", help="delete every row first")
    args = parser.parse_args()
    Path(args.data).mkdir(parents=True, exist_ok=True)
    conn = connect(os.path.join(args.data, "rotator.db"))
    try:
        init_db(conn)
        seed(conn, reset=args.reset)
        counts = {
            name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("students", "jobs", "volunteers")
        }
    finally:
        conn.close()
    print(
        f"Seeded {args.data}: {counts['students']} students, {counts['jobs']} jobs, "
        f"{counts['volunteers']} volunteer links, start_date {START_DATE}"
        + (" (reset first)" if args.reset else ""))


if __name__ == "__main__":
    main()
