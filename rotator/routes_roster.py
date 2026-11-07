"""Roster API routes: students, jobs, volunteers."""
from flask import Blueprint, jsonify, request

from .app import get_conn
from .roster import (
    add_job,
    add_student,
    archive_job,
    archive_student,
    list_jobs,
    list_students,
    rename_student,
    reorder_jobs,
    set_volunteers,
    update_job,
)
from .routes_common import json_body, require_pin, request_today

bp = Blueprint("roster", __name__, url_prefix="/api")


def _include_archived() -> bool:
    """True when the query asks for archived rows too."""
    return request.args.get("include_archived") == "1"


@bp.get("/students")
def api_students():
    """List students (active only unless include_archived=1)."""
    return jsonify({"students": list_students(get_conn(), _include_archived())})


@bp.post("/students")
@require_pin
def api_add_student():
    """Add a student (201) or re-activate an archived twin (200)."""
    body = json_body()
    view, reactivated = add_student(get_conn(), body.get("name", ""))
    return jsonify(view), (200 if reactivated else 201)


@bp.patch("/students/<int:student_id>")
@require_pin
def api_rename_student(student_id: int):
    """Rename a student."""
    return jsonify(rename_student(get_conn(), student_id, json_body().get("name", "")))


@bp.delete("/students/<int:student_id>")
@require_pin
def api_archive_student(student_id: int):
    """Archive a student (keeps history, removes future assignments)."""
    archive_student(get_conn(), student_id, request_today())
    return jsonify({"ok": True})


@bp.get("/jobs")
def api_jobs():
    """List jobs with volunteer_ids (active only unless include_archived=1)."""
    return jsonify({"jobs": list_jobs(get_conn(), _include_archived())})


@bp.post("/jobs")
@require_pin
def api_add_job():
    """Create a job with optional volunteers (201, or 200 when re-activating)."""
    body = json_body()
    view, reactivated = add_job(
        get_conn(),
        body.get("name", ""),
        body.get("description", ""),
        body.get("icon", ""),
        body.get("volunteer_ids") or [],
    )
    return jsonify(view), (200 if reactivated else 201)


@bp.patch("/jobs/<int:job_id>")
@require_pin
def api_update_job(job_id: int):
    """Update any of name, description, icon on a job."""
    body = json_body()
    return jsonify(update_job(get_conn(), job_id,
                              name=body.get("name"),
                              description=body.get("description"),
                              icon=body.get("icon")))


@bp.delete("/jobs/<int:job_id>")
@require_pin
def api_archive_job(job_id: int):
    """Archive a job (keeps history, removes future assignments)."""
    archive_job(get_conn(), job_id, request_today())
    return jsonify({"ok": True})


@bp.post("/jobs/reorder")
@require_pin
def api_reorder_jobs():
    """Set job sort order from an explicit ids list."""
    reorder_jobs(get_conn(), json_body().get("ids", []))
    return jsonify({"ok": True})


@bp.put("/jobs/<int:job_id>/volunteers")
@require_pin
def api_set_volunteers(job_id: int):
    """Replace a job's volunteer set."""
    return jsonify(set_volunteers(get_conn(), job_id, json_body().get("student_ids", [])))
