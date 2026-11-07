"""Tests for export/import backup (round-trip and error handling)."""
from rotator.app import create_app

PIN = "1234"
HEADERS = {"X-Admin-Pin": PIN}
TODAY = "2026-11-06"
MONTH = "2026-11"


def _make_app(tmp_path, pin: str = PIN):
    """A test app on a throwaway directory, with the given PIN."""
    return create_app(
        {
            "DATA_DIR": str(tmp_path),
            "ADMIN_PIN": pin,
            "ALLOW_TODAY_OVERRIDE": True,
        }
    )


def _seed(client) -> None:
    """Seed students, a job with volunteers, and a cancelled session via the API."""
    for name in ("Yusuf", "Maryam", "Omar", "Layla"):
        assert client.post("/api/students", json={"name": name}, headers=HEADERS).status_code == 201
    resp = client.post(
        "/api/jobs",
        json={"name": "Mu'adhin", "volunteer_ids": [1, 2, 3, 4]},
        headers=HEADERS,
    )
    assert resp.status_code == 201
    resp = client.post("/api/sessions/2026-11-07/cancel", json={"note": "Away"}, headers=HEADERS)
    assert resp.status_code == 200


def test_export_requires_pin(tmp_path):
    """GET /api/export is a PIN-protected route."""
    client = _make_app(tmp_path).test_client()
    _seed(client)
    resp = client.get("/api/export")
    assert resp.status_code == 401
    resp = client.get("/api/export", headers=HEADERS)
    assert resp.status_code == 200
    dump = resp.get_json()
    assert dump["version"] == 1
    assert dump["exported_at"]
    assert {t: len(rows) for t, rows in dump["tables"].items()} == {
        "students": 4, "jobs": 1, "volunteers": 4, "sessions": 1,
        "assignments": 0, "settings": 1,
    }


def test_export_import_round_trip(tmp_path):
    """Export then import into a differently-seeded app: /api/calendar JSON is identical."""
    app1, app2 = _make_app(tmp_path / "a"), _make_app(tmp_path / "b")
    c1, c2 = app1.test_client(), app2.test_client()
    _seed(c1)
    assert c2.post("/api/students", json={"name": "Zayd"}, headers=HEADERS).status_code == 201
    assert c2.get("/api/students", headers=HEADERS).get_json()["students"][0]["name"] == "Zayd"

    dump = c1.get("/api/export", headers=HEADERS).get_json()
    resp = c2.post("/api/import", json=dump, headers=HEADERS)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json() == {"ok": True}

    cal = f"/api/calendar?today={TODAY}&month={MONTH}"
    assert c1.get(cal).get_json() == c2.get(cal).get_json()
    names = [s["name"] for s in c2.get("/api/students", headers=HEADERS).get_json()["students"]]
    assert names == ["Layla", "Maryam", "Omar", "Yusuf"]
    # Cancel Sunday too in app1, re-export/re-import, then /api/today matches as well.
    assert c1.post("/api/sessions/2026-11-08/cancel", json={}, headers=HEADERS).status_code == 200
    dump = c1.get("/api/export", headers=HEADERS).get_json()
    assert c2.post("/api/import", json=dump, headers=HEADERS).status_code == 200
    assert c1.get("/api/today?today=" + TODAY).get_json() == c2.get("/api/today?today=" + TODAY).get_json()
    assert c1.get("/api/today?today=" + TODAY).get_json()["next_held"] is not None


def test_import_requires_pin(tmp_path):
    """POST /api/import is a PIN-protected route."""
    client = _make_app(tmp_path).test_client()
    resp = client.post("/api/import", json={"version": 1, "tables": _empty_tables()})
    assert resp.status_code == 401


def test_import_bad_version_leaves_db_unchanged(tmp_path):
    """version 2 → 400 and nothing in the database changes."""
    client = _make_app(tmp_path).test_client()
    _seed(client)
    listing_before = client.get("/api/students", headers=HEADERS).get_json()

    dump = {"version": 2, "tables": _empty_tables()}
    resp = client.post("/api/import", json=dump, headers=HEADERS)
    assert resp.status_code == 400

    assert client.get("/api/students", headers=HEADERS).get_json() == listing_before
    assert client.get("/api/jobs", headers=HEADERS).get_json()["jobs"][0]["name"] == "Mu'adhin"


def test_import_garbage_leaves_db_unchanged(tmp_path):
    """Bad shapes (non-object, wrong types, unknown tables) → 400; database intact."""
    client = _make_app(tmp_path).test_client()
    _seed(client)
    before = client.get("/api/students?include_archived=1", headers=HEADERS).get_json()

    cases = [
        "just a string",
        None,
        {"version": 1},  # no tables
        {"version": 1, "tables": {"students": [{}, {"name": 3}]}},  # missing/wrong types
        {"version": 1, "tables": {t: [] for t in _empty_tables() if t != "settings"}},  # missing one table
    ]
    for body in cases:
        resp = client.post("/api/import", json=body, headers=HEADERS)
        assert resp.status_code == 400, (body, resp.get_data(as_text=True))

    assert client.get("/api/students?include_archived=1", headers=HEADERS).get_json() == before
    assert client.get("/api/students", headers=HEADERS).get_json() == before


def _empty_tables() -> dict:
    """An empty but well-formed table set."""
    return {name: [] for name in ("students", "jobs", "volunteers",
                                  "sessions", "assignments", "settings")}

