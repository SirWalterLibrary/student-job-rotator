"""Read API routes: config, today, calendar, queue."""
import re

from datetime import date

from flask import Blueprint, current_app, jsonify, request

from .app import get_conn
from .dates import TZ, month_class_days, next_class_day_after, parse_iso, upcoming_weekend
from .errors import RotatorError
from .routes_common import request_today
from .schedule import (
    WEEKDAYS,
    build_sessions,
    cancelled_dates,
    get_start_date,
    queue_status,
)

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
WINDOW_MONTHS = 24

bp = Blueprint("schedule", __name__, url_prefix="/api")


def _ym_index(year: int, month: int) -> int:
    """Orderable index of a (year, month) pair."""
    return year * 12 + (month - 1)


def _shift_month(ym: str, delta: int) -> str:
    """Return the YYYY-MM string offset by delta months."""
    year, month = (int(part) for part in ym.split("-"))
    total = _ym_index(year, month) + delta
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _month_window(conn, today: date) -> tuple[int, int]:
    """Inclusive (low, high) month indices: month of start .. 24 months after today."""
    start = get_start_date(conn, today)
    return _ym_index(start.year, start.month), _ym_index(today.year, today.month) + WINDOW_MONTHS


@bp.get("/config")
def api_config():
    """Shared settings the frontend needs (today, weekday, timezone, pin, start_date)."""
    today = request_today()
    conn = get_conn()
    start = get_start_date(conn, today)
    return jsonify({
        "today": today.isoformat(),
        "weekday": WEEKDAYS[today.weekday()],
        "timezone": str(TZ),
        "pin_required": bool(current_app.config["ADMIN_PIN"]),
        "start_date": start.isoformat(),
    })


@bp.get("/today")
def api_today():
    """Today's session on Sat/Sun, or the next weekend on Mon-Fri."""
    today = request_today()
    conn = get_conn()
    days = upcoming_weekend(today)
    sessions = build_sessions(conn, today, days[0], days[-1])
    mode = "today" if len(days) == 1 else "upcoming"
    next_held = None
    if all(s["status"] == "cancelled" for s in sessions):
        last = parse_iso(sessions[-1]["date"])
        nxt = next_class_day_after(last, cancelled_dates(conn))
        next_held = build_sessions(conn, today, nxt, nxt)[0]
    return jsonify({
        "today": today.isoformat(),
        "weekday": WEEKDAYS[today.weekday()],
        "mode": mode,
        "heading": "Today" if mode == "today" else "Next weekend",
        "sessions": sessions,
        "next_held": next_held,
    })


@bp.get("/calendar")
def api_calendar():
    """Session views for every class day of a month."""
    today = request_today()
    conn = get_conn()
    raw = request.args.get("month")
    if raw is None:
        ym = f"{today.year:04d}-{today.month:02d}"
    elif _MONTH_RE.match(raw):
        ym = raw
    else:
        raise RotatorError("month must be YYYY-MM", 400)
    year, month = (int(part) for part in ym.split("-"))
    low, high = _month_window(conn, today)
    if not low <= _ym_index(year, month) <= high:
        raise RotatorError("month is outside the allowed window", 400)
    start = get_start_date(conn, today)
    days = [d for d in month_class_days(year, month) if d >= start]
    sessions = build_sessions(conn, today, days[0], days[-1])
    return jsonify({
        "month": ym,
        "label": f"{MONTH_NAMES[month - 1]} {year}",
        "prev": _shift_month(ym, -1) if _ym_index(year, month) > low else None,
        "next": _shift_month(ym, 1) if _ym_index(year, month) < high else None,
        "sessions": sessions,
    })


@bp.get("/queue")
def api_queue():
    """Up-next queue, one entry per active job."""
    return jsonify({"jobs": queue_status(get_conn(), request_today())})
