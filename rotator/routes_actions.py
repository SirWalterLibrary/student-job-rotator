"""Action API routes: absent swap, cancel/restore, manual assignments, settings."""
from datetime import date

from flask import Blueprint, jsonify, request

from .actions import cancel_session, clear_assignment, restore_session, set_manual, swap_absent
from .app import get_conn
from .dates import parse_iso
from .errors import RotatorError
from .routes_common import json_body, require_pin, request_today
from .schedule import build_sessions, set_start_date

bp = Blueprint("actions", __name__, url_prefix="/api")


def _parse_date(raw: str) -> date:
    """Parse a route date parameter (400 unless YYYY-MM-DD)."""
    try:
        return parse_iso(raw)
    except ValueError:
        raise RotatorError("date must be YYYY-MM-DD", 400)


def _session_view(conn, today: date, d: date) -> dict:
    """The rebuilt session view for one date."""
    return build_sessions(conn, today, d, d)[0]


@bp.post("/sessions/<date_str>/absent")
@require_pin
def api_absent(date_str: str):
    """Mark the student holding a job as absent; swap in a partner or leave vacant."""
    body = json_body()
    result = swap_absent(
        get_conn(), request_today(), date_str, body.get("job_id"),
        partner_id=body.get("partner_id"), vacant=bool(body.get("vacant", False)))
    return jsonify(result)


@bp.post("/sessions/<date_str>/cancel")
@require_pin
def api_cancel(date_str: str):
    """Cancel a class day (teacher away)."""
    cancel_session(get_conn(), request_today(), date_str,
                   json_body().get("note") or "")
    return jsonify({"ok": True})


@bp.post("/sessions/<date_str>/restore")
@require_pin
def api_restore(date_str: str):
    """Restore a cancelled day to held."""
    restore_session(get_conn(), request_today(), date_str)
    return jsonify({"ok": True})


@bp.put("/sessions/<date_str>/assignments/<int:job_id>")
@require_pin
def api_set_assignment(date_str: str, job_id: int):
    """Manual override: set a volunteer on a job for a day; returns the session view."""
    body = json_body()
    today = request_today()
    conn = get_conn()
    d = _parse_date(date_str)
    set_manual(conn, today, d.isoformat(), job_id, body.get("student_id"))
    return jsonify(_session_view(conn, today, d))


@bp.delete("/sessions/<date_str>/assignments/<int:job_id>")
@require_pin
def api_clear_assignment(date_str: str, job_id: int):
    """Clear the stored row for a slot; returns the session view minus that role."""
    return jsonify(clear_assignment(get_conn(), request_today(), date_str, job_id))


@bp.put("/settings")
@require_pin
def api_set_settings():
    """Set the roster start date (Sat/Sun; not after any frozen session)."""
    body = json_body()
    if not isinstance(body.get("start_date"), str):
        raise RotatorError("start_date must be a YYYY-MM-DD string", 400)
    start = set_start_date(get_conn(), request_today(), body["start_date"])
    return jsonify({"start_date": start.isoformat()})
