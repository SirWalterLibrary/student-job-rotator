"""Tests for the roster API (students, jobs, volunteers)."""
from rotator.app import get_conn
from rotator.db import utc_now_iso


def _add_student(client, name: str) -> dict:
    """Create a student via the API and return its view."""
    resp = client.post("/api/students", json={"name": name})
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


def _add_job(client, name: str, **extra) -> dict:
    """Create a job via the API and return its view."""
    resp = client.post("/api/jobs", json={"name": name, **extra})
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


def test_student_lifecycle(client):
    """Add, list, rename, archive a student through the API."""
    resp = client.post("/api/students", json={"name": "Yusuf"})
    assert resp.status_code == 201
    student = resp.get_json()
    assert student == {"id": 1, "name": "Yusuf", "active": True}

    listing = client.get("/api/students").get_json()["students"]
    assert [s["name"] for s in listing] == ["Yusuf"]

    resp = client.patch(f"/api/students/{student['id']}", json={"name": "Yusuf A."})
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Yusuf A."

    resp = client.delete(f"/api/students/{student['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    assert client.get("/api/students").get_json()["students"] == []


def test_duplicate_student_name_409(client):
    """A case-insensitive duplicate active name is rejected."""
    _add_student(client, "Yusuf")
    resp = client.post("/api/students", json={"name": "yusuf"})
    assert resp.status_code == 409
    assert "error" in resp.get_json()


def test_readd_archived_name_reactivates_same_id(client):
    """Re-adding an archived name re-activates the same row (200, not 201)."""
    student = _add_student(client, "Yusuf")
    assert client.delete(f"/api/students/{student['id']}").status_code == 200
    resp = client.post("/api/students", json={"name": "Yusuf"})
    assert resp.status_code == 200
    assert resp.get_json() == {"id": student["id"], "name": "Yusuf", "active": True}


def test_invalid_names_400(client):
    """Empty (or whitespace) and 41-character names are rejected."""
    assert client.post("/api/students", json={"name": "   "} ).status_code == 400
    assert client.post("/api/students", json={"name": "a" * 41}).status_code == 400


def test_add_job_with_volunteers(client):
    """A new job gets max+1 sort_order and its volunteers in the order given."""
    ids = [_add_student(client, n)["id"] for n in ("Yusuf", "Maryam", "Hana")]
    job = _add_job(client, "Mu'adhin", description="Calls the adhan", icon="🕌",
                   volunteer_ids=ids)
    assert job["volunteer_ids"] == ids
    assert job["sort_order"] == 0
    jobs = client.get("/api/jobs").get_json()["jobs"]
    assert jobs[0]["id"] == job["id"]
    assert jobs[0]["volunteer_ids"] == ids


def test_update_job(client):
    """PATCH updates any of name, description, icon."""
    job = _add_job(client, "Mu'adhin")
    resp = client.patch(f"/api/jobs/{job['id']}",
                        json={"description": "Calls the adhan", "icon": "🕌"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Mu'adhin" and body["description"] == "Calls the adhan" and body["icon"] == "🕌"
    resp = client.patch(f"/api/jobs/{job['id']}", json={"name": "Adhan"})
    assert resp.status_code == 200 and resp.get_json()["name"] == "Adhan"


def test_archive_job(client):
    """An archived job disappears from the list but returns with include_archived=1."""
    job = _add_job(client, "Cleaner")
    assert client.delete(f"/api/jobs/{job['id']}").status_code == 200
    assert client.get("/api/jobs").get_json()["jobs"] == []
    jobs = client.get("/api/jobs?include_archived=1").get_json()["jobs"]
    assert [j["id"] for j in jobs] == [job["id"]]
    assert jobs[0]["active"] is False


def test_reorder_jobs(client):
    """Reorder sets sort_order 0..n-1 in the given order."""
    a = _add_job(client, "Alpha")
    b = _add_job(client, "Beta")
    c = _add_job(client, "Gamma")
    resp = client.post("/api/jobs/reorder", json={"ids": [c["id"], a["id"], b["id"]]})
    assert resp.status_code == 200
    jobs = client.get("/api/jobs").get_json()["jobs"]
    assert [j["name"] for j in jobs] == ["Gamma", "Alpha", "Beta"]
    assert [j["sort_order"] for j in jobs] == [0, 1, 2]


def test_reorder_wrong_ids_400(client):
    """Reorder with ids that are not exactly the active set is rejected."""
    a = _add_job(client, "Alpha")
    b = _add_job(client, "Beta")
    assert client.post("/api/jobs/reorder", json={"ids": [a["id"]]}).status_code == 400
    assert client.post("/api/jobs/reorder", json={"ids": [a["id"], b["id"], 999]}).status_code == 400


def test_set_volunteers_adds_removes_keeps_joined_at(client, app):
    """PUT volunteers keeps joined_at for kept students, adds new, drops removed."""
    a = _add_student(client, "Yusuf")["id"]
    b = _add_student(client, "Maryam")["id"]
    c = _add_student(client, "Hana")["id"]
    job = _add_job(client, "Mu'adhin")["id"]
    assert client.put(f"/api/jobs/{job}/volunteers",
                      json={"student_ids": [a, b]}).status_code == 200
    with app.app_context():
        joined_b = get_conn().execute(
            "SELECT joined_at FROM volunteers WHERE job_id = ? AND student_id = ?",
            (job, b)).fetchone()["joined_at"]
    resp = client.put(f"/api/jobs/{job}/volunteers", json={"student_ids": [b, c]})
    assert resp.status_code == 200
    assert resp.get_json()["volunteer_ids"] == [b, c]
    with app.app_context():
        conn = get_conn()
        assert conn.execute(
            "SELECT joined_at FROM volunteers WHERE job_id = ? AND student_id = ?",
            (job, b)).fetchone()["joined_at"] == joined_b
        assert conn.execute(
            "SELECT COUNT(*) FROM volunteers WHERE job_id = ? AND student_id = ?",
            (job, a)).fetchone()[0] == 0


def test_set_volunteers_rejects_archived_and_unknown_400(client):
    """Archived or unknown student ids are rejected and nothing changes."""
    a = _add_student(client, "Yusuf")["id"]
    b = _add_student(client, "Maryam")["id"]
    client.delete(f"/api/students/{b}")
    job = _add_job(client, "Mu'adhin")["id"]
    assert client.put(f"/api/jobs/{job}/volunteers",
                      json={"student_ids": [a, b]}).status_code == 400
    assert client.put(f"/api/jobs/{job}/volunteers",
                      json={"student_ids": [a, 999]}).status_code == 400


def test_archive_student_removes_from_volunteer_ids(client):
    """Archiving a student drops them from every job's volunteer list."""
    a = _add_student(client, "Yusuf")["id"]
    b = _add_student(client, "Maryam")["id"]
    j1 = _add_job(client, "Mu'adhin", volunteer_ids=[a, b])["id"]
    j2 = _add_job(client, "Cleaner", volunteer_ids=[a, b])["id"]
    assert client.delete(f"/api/students/{a}").status_code == 200
    jobs = {j["id"]: j for j in client.get("/api/jobs").get_json()["jobs"]}
    assert jobs[j1]["volunteer_ids"] == [b]
    assert jobs[j2]["volunteer_ids"] == [b]


def test_archive_removes_future_assignment_keeps_past(client, app):
    """With today=2026-11-06, a 2026-11-14 row goes but a 2026-11-01 row stays."""
    s = _add_student(client, "Yusuf")["id"]
    j = _add_job(client, "Mu'adhin")["id"]
    with app.app_context():
        conn = get_conn()
        for d in ("2026-11-01", "2026-11-14"):
            conn.execute(
                "INSERT INTO assignments (date, job_id, student_id, source, note, created_at) "
                "VALUES (?, ?, ?, 'auto', '', ?)", (d, j, s, utc_now_iso()))
        conn.commit()
    assert client.delete(f"/api/students/{s}?today=2026-11-06").status_code == 200
    with app.app_context():
        dates = [r["date"] for r in get_conn().execute(
            "SELECT date FROM assignments WHERE student_id = ? ORDER BY date", (s,))]
    assert dates == ["2026-11-01"]


def test_include_archived_shows_archived(client):
    """include_archived=1 lists archived students and jobs."""
    s = _add_student(client, "Yusuf")["id"]
    j = _add_job(client, "Mu'adhin")["id"]
    client.delete(f"/api/students/{s}")
    client.delete(f"/api/jobs/{j}")
    students = client.get("/api/students?include_archived=1").get_json()["students"]
    jobs = client.get("/api/jobs?include_archived=1").get_json()["jobs"]
    assert [st["id"] for st in students] == [s] and students[0]["active"] is False
    assert [jb["id"] for jb in jobs] == [j] and jobs[0]["active"] is False
