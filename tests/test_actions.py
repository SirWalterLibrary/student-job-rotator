"""Tests for the action routes: absent swap, cancel/restore, next_held."""
from rotator.app import get_conn

from tests.helpers import make_job, make_students

SAT, SUN = "2026-11-07", "2026-11-08"


def _seed(app, names, job_vols: dict) -> tuple[dict, dict]:
    """Create students and jobs (job name -> volunteer names); return id maps."""
    sids, jids = {}, {}
    with app.app_context():
        conn = get_conn()
        for name in names:
            sids[name] = make_students(conn, [name])[0]
        for job, vols in job_vols.items():
            jids[job] = make_job(conn, job, student_ids=[sids[v] for v in vols])
    return sids, jids


def _get(client, path: str, today: str, **query) -> dict:
    """GET a path with ?today= and extra query; return parsed JSON (asserting 200)."""
    from urllib.parse import urlencode
    qs = urlencode({"today": today, **query})
    resp = client.get(f"{path}?{qs}")
    assert resp.status_code == 200, (path, today, resp.get_data(as_text=True))
    return resp.get_json()


def _role(session: dict, job_id: int):
    """The role for a job in a session (None if nobody is on it)."""
    return next((r for r in session["roles"] if r["job"]["id"] == job_id), None)


def _who(session: dict, job_id: int):
    """The student name on a job in a session (None if nobody is on it)."""
    role = _role(session, job_id)
    return role["student"]["name"] if role is not None else None


def _calendar_day(client, month: str, today: str, iso_date: str, job_id: int):
    """One session from a calendar month, addressed by date."""
    cal = _get(client, "/api/calendar", today, month=month)
    return next(s for s in cal["sessions"] if s["date"] == iso_date)


def test_swap_absent_books_cover_and_makeup(client, app):
    """A absent Saturday: the projected Sunday student covers, A takes Sunday, C goes next."""
    sids, jids = _seed(app, ["Yusuf", "Maryam", "Hana"],
                       {"Mu'adhin": ["Yusuf", "Maryam", "Hana"]})
    j = jids["Mu'adhin"]
    resp = client.post(f"/api/sessions/{SAT}/absent?today=2026-11-06", json={"job_id": j})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["date"] == SAT and body["next_date"] == SUN
    assert body["absent"] == {"id": sids["Yusuf"], "name": "Yusuf"}
    assert body["covering"]["name"] == "Maryam"
    role = _role(_get(client, "/api/today", SAT)["sessions"][0], j)
    assert role["student"]["name"] == "Maryam"
    assert role["source"] == "swap"
    assert role["note"] == "Covering for Yusuf (absent)"
    assert _who(_get(client, "/api/today", SUN)["sessions"][0], j) == "Yusuf"
    sat2 = _get(client, "/api/today", "2026-11-14")["sessions"][0]
    sun2 = _get(client, "/api/today", "2026-11-15")["sessions"][0]
    assert [_who(sat2, j), _who(sun2, j)] == ["Hana", "Maryam"]


def test_swap_rejects_invalid_partners_and_dates(client, app):
    """Busy partner, absent student busy next day, locked slot, self, and past dates are refused."""
    sids, jids = _seed(app, ["Yusuf", "Maryam", "Hana"],
                       {"Mu'adhin": ["Yusuf", "Maryam", "Hana"],
                        "Cleaner": ["Yusuf", "Maryam"]})
    j1, j2 = jids["Mu'adhin"], jids["Cleaner"]
    _get(client, "/api/today", SAT)
    r = client.post(f"/api/sessions/{SAT}/absent?today={SAT}",
                    json={"job_id": j1, "partner_id": sids["Maryam"]})
    assert r.status_code == 409                      # partner already has a role that day
    r = client.post(f"/api/sessions/{SAT}/absent?today={SAT}",
                    json={"job_id": j1, "partner_id": sids["Hana"]})
    assert r.status_code == 409                      # A already has a role on Sunday
    r = client.post(f"/api/sessions/{SAT}/absent?today={SAT}",
                    json={"job_id": j1, "partner_id": sids["Yusuf"]})
    assert r.status_code == 409                      # partner is the absent student
    r = client.post(f"/api/sessions/{SAT}/absent?today={SAT}",
                    json={"job_id": j2, "partner_id": sids["Hana"]})
    assert r.status_code == 409                      # Hana is not a volunteer of Cleaner
    r = client.post("/api/sessions/2026-10-31/absent?today=2026-11-07",
                    json={"job_id": j1})
    assert r.status_code == 400                      # past date


def test_swap_rejects_occupied_locked_slot(client, app):
    """A manual row already occupying the next day's slot blocks the swap."""
    sids, jids = _seed(app, ["Yusuf", "Maryam"], {"Mu'adhin": ["Yusuf", "Maryam"]})
    j = jids["Mu'adhin"]
    _get(client, "/api/today", SAT)
    _get(client, "/api/today", SUN)      # freeze Sunday too, so Yusuf holds it (not Maryam)
    assert client.put(f"/api/sessions/{SUN}/assignments/{j}?today={SAT}",
                      json={"student_id": sids["Maryam"]}).status_code == 200
    r = client.post(f"/api/sessions/{SAT}/absent?today={SAT}",
                    json={"job_id": j, "partner_id": sids["Maryam"]})
    assert r.status_code == 409


def test_swap_vacant_leaves_job_empty(client, app):
    """vacant=true removes the row; the absent student is first in the queue next session."""
    sids, jids = _seed(app, ["Yusuf", "Maryam"], {"Mu'adhin": ["Yusuf", "Maryam"]})
    j = jids["Mu'adhin"]
    r = client.post(f"/api/sessions/{SAT}/absent?today={SAT}",
                    json={"job_id": j, "vacant": True})
    assert r.status_code == 200
    assert _role(r.get_json(), j) is None                    # the slot shows empty
    assert _who(_get(client, "/api/today", SUN)["sessions"][0], j) == "Yusuf"
    with app.app_context():
        assert get_conn().execute(
            "SELECT COUNT(*) c FROM assignments WHERE date = ?", (SAT,)).fetchone()["c"] == 0


def test_cancel_shifts_sunday(client, app):
    """Cancelling Saturday: no roles, and Sunday takes what Saturday would have been."""
    _, jids = _seed(app, ["Yusuf", "Maryam"], {"Mu'adhin": ["Yusuf", "Maryam"]})
    j = jids["Mu'adhin"]
    _get(client, "/api/today", SAT)
    assert client.post(f"/api/sessions/{SAT}/cancel?today={SAT}",
                       json={"note": "Teacher away"}).status_code == 200
    assert client.post(f"/api/sessions/{SAT}/cancel?today={SAT}",
                       json={}).status_code == 409               # already cancelled
    sat = _calendar_day(client, "2026-11", SUN, SAT, j)
    assert sat["status"] == "cancelled" and sat["roles"] == [] and sat["note"] == "Teacher away"
    assert _who(_calendar_day(client, "2026-11", SUN, SUN, j), j) == "Yusuf"
    with app.app_context():
        assert get_conn().execute(
            "SELECT COUNT(*) c FROM assignments WHERE date = ?", (SAT,)).fetchone()["c"] == 0


def test_cancel_deletes_swap_counterpart(client, app):
    """Cancelling a swapped Saturday also deletes the make-up row on Sunday."""
    _, jids = _seed(app, ["Yusuf", "Maryam"], {"Mu'adhin": ["Yusuf", "Maryam"]})
    j = jids["Mu'adhin"]
    assert client.post(f"/api/sessions/{SAT}/absent?today=2026-11-06",
                       json={"job_id": j}).status_code == 200
    assert client.post(f"/api/sessions/{SAT}/cancel?today={SAT}",
                       json={}).status_code == 200
    with app.app_context():
        conn = get_conn()
        assert conn.execute("SELECT COUNT(*) c FROM assignments WHERE date = ?",
                            (SAT,)).fetchone()["c"] == 0
        assert conn.execute("SELECT COUNT(*) c FROM assignments WHERE date = ? AND job_id = ?",
                            (SUN, j)).fetchone()["c"] == 0


def test_restore_shifts_turns_back(client, app):
    """Restore Saturday: the day re-fills and the shifted turn moves back."""
    _, jids = _seed(app, ["Yusuf", "Maryam"], {"Mu'adhin": ["Yusuf", "Maryam"]})
    j = jids["Mu'adhin"]
    _get(client, "/api/today", SAT)
    assert client.post(f"/api/sessions/{SAT}/cancel?today={SAT}", json={}).status_code == 200
    assert client.post(f"/api/sessions/{SAT}/restore?today={SAT}").status_code == 200
    assert client.post(f"/api/sessions/{SAT}/restore?today={SAT}").status_code == 409
    sat = _get(client, "/api/today", SAT)["sessions"][0]
    assert sat["status"] == "held" and _who(sat, j) == "Yusuf"
    assert _who(_calendar_day(client, "2026-11", SUN, SUN, j), j) == "Maryam"


def test_next_held_skips_a_cancelled_weekend(client, app):
    """With both weekend days cancelled, next_held is the following Saturday."""
    _seed(app, ["Yusuf"], {"Mu'adhin": ["Yusuf"]})
    assert client.post(f"/api/sessions/{SAT}/cancel?today={SAT}", json={}).status_code == 200
    assert client.post(f"/api/sessions/{SUN}/cancel?today={SUN}", json={}).status_code == 200
    body = _get(client, "/api/today", "2026-11-06")          # Friday shows the whole weekend
    assert [s["status"] for s in body["sessions"]] == ["cancelled", "cancelled"]
    assert body["next_held"]["date"] == "2026-11-14"
