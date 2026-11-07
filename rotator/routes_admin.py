"""Admin API routes: PIN auth, export backup, import backup."""
from flask import Blueprint, current_app, jsonify, request

from .app import get_conn
from .auth import limiter, pin_ok
from .db import utc_now_iso
from .errors import RotatorError
from .routes_common import json_body, require_pin

bp = Blueprint("admin", __name__, url_prefix="/api")

_TABLES = {
    "students": ["id", "name", "active", "created_at"],
    "jobs": ["id", "name", "description", "icon", "sort_order", "active", "created_at"],
    "volunteers": ["job_id", "student_id", "joined_at"],
    "sessions": ["date", "status", "frozen", "note"],
    "assignments": ["id", "date", "job_id", "student_id", "source", "note", "group_id", "created_at"],
    "settings": ["key", "value"],
}

_INTS = {"id", "job_id", "student_id", "sort_order", "active", "frozen"}
_STRINGS = {"name", "description", "icon", "joined_at", "date", "status",
            "note", "source", "group_id", "created_at", "key", "value"}
_NULLABLE = {"group_id"}


def _check_row(table: str, row) -> None:
    """400 unless the row has every column of its table with the right type."""
    if not isinstance(row, dict):
        raise RotatorError("Each table must be a list of row objects", 400)
    for column in _TABLES[table]:
        if column not in row:
            raise RotatorError(f"{table} row missing {column}", 400)
        value = row[column]
        if column in _INTS:
            if not isinstance(value, int) or isinstance(value, bool):
                raise RotatorError(f"{table}.{column} must be an integer", 400)
        elif value is not None and not isinstance(value, str):
            if column not in _NULLABLE:
                raise RotatorError(f"{table}.{column} must be a string", 400)
    if row.get("group_id") is not None and not isinstance(row["group_id"], str):
        raise RotatorError("assignments.group_id must be a string or null", 400)


def _validate_dump(data) -> None:
    """400 unless the body is a well-formed version 1 export dump."""
    if not isinstance(data, dict):
        raise RotatorError("Import body must be a JSON object", 400)
    if data.get("version") != 1:
        raise RotatorError("version must be 1", 400)
    tables = data.get("tables")
    if not isinstance(tables, dict):
        raise RotatorError("tables must be an object", 400)
    for name in _TABLES:
        rows = tables.get(name)
        if not isinstance(rows, list):
            raise RotatorError(f"tables.{name} must be a list", 400)
        for row in rows:
            _check_row(name, row)


@bp.post("/auth")
def api_auth():
    """Check the teacher PIN from the body (rate limited per IP)."""
    body = json_body()
    provided = body.get("pin")
    if not isinstance(provided, str):
        raise RotatorError("pin must be a string", 400)
    key = request.remote_addr or "unknown"
    lim = limiter()
    if lim.blocked(key):
        return jsonify({"error": "Too many failed attempts, try again later"}), 429
    if pin_ok(current_app.config, provided):
        return jsonify({"ok": True})
    lim.record(key)
    return jsonify({"error": "Invalid PIN"}), 401


@bp.get("/export")
@require_pin
def api_export():
    """Full JSON dump of every table (the supported backup)."""
    conn = get_conn()
    tables = {name: [dict(row) for row in conn.execute(f"SELECT * FROM {name}")]
              for name in _TABLES}
    return jsonify({
        "version": 1,
        "exported_at": utc_now_iso(),
        "tables": tables,
    })


@bp.post("/import")
@require_pin
def api_import():
    """Replace the whole database with a version 1 export dump (one transaction)."""
    _validate_dump(json_body())
    conn = get_conn()
    data = request.get_json(silent=True)
    try:
        with conn:  # one transaction; rolls back if anything fails
            for name in ("assignments", "sessions", "volunteers", "jobs", "students", "settings"):
                conn.execute(f"DELETE FROM {name}")
            for name, columns in _TABLES.items():
                for row in data["tables"][name]:
                    sql = f"INSERT INTO {name} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})"
                    conn.execute(sql, [row[c] for c in columns])
    except RotatorError:
        raise
    except Exception as err:
        raise RotatorError(f"Import failed: {err.__class__.__name__}", 400)
    return jsonify({"ok": True})
