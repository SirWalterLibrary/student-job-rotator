"""Tests for manual/clear assignments, start-date settings, and read-side walker behavior."""
from rotator.app import get_conn

from tests.test_actions import _get, _role, _seed, _who, SAT, SUN


def test_freeze_is_idempotent(client, app):
    """First read freezes Saturday with one auto row per job; a second read changes nothing."""
    _seed(app, ["Yusuf"], {"Mu'adhin": ["Yusuf"]})
    client.get(f"/api/today?today={SAT}")
    with app.app_context():
        conn = get_conn()
        rows = conn.execute("SELECT source FROM assignments WHERE date = ?", (SAT,)).fetchall()
        frozen = conn.execute("SELECT frozen FROM sessions WHERE date = ?", (SAT,)).fetchone()["frozen"]
    assert [r["source"] for r in rows] == ["auto"]
    assert frozen == 1
    client.get(f"/api/today?today={SAT}")
    with app.app_context():
        assert get_conn().execute("SELECT COUNT(*) c FROM assignments").fetchone()["c"] == 1


def test_friday_stores_nothing(client, app):
    """A Friday read shows the whole weekend as projected and stores nothing."""
    _seed(app, ["Yusuf", "Maryam"], {"Mu'adhin": ["Yusuf", "Maryam"]})
    body = _get(client, "/api/today", "2026-11-06")
    assert all(r["projected"] is True for s in body["sessions"] for r in s["roles"])
    with app.app_context():
        conn = get_conn()
        assert conn.execute("SELECT COUNT(*) c FROM assignments").fetchone()["c"] == 0
        assert conn.execute("SELECT COUNT(*) c FROM sessions").fetchone()["c"] == 0


def test_nobody_holds_two_roles_in_one_day(client, app):
    """With two multi-volunteer jobs, Saturday then Sunday never give a student two roles."""
    sids, jids = _seed(app, ["Yusuf", "Maryam", "Hana"],
                       {"Mu'adhin": ["Yusuf", "Maryam", "Hana"],
                        "Cleaner": ["Yusuf", "Maryam", "Hana"]})
    j1, j2 = jids["Mu'adhin"], jids["Cleaner"]
    sat = _get(client, "/api/today", SAT)["sessions"][0]
    sun = _get(client, "/api/today", SUN)["sessions"][0]
    assert {_who(sat, j1), _who(sat, j2)} == {"Yusuf", "Maryam"}
    assert {_who(sun, j1), _who(sun, j2)} == {"Maryam", "Yusuf"}
    for session in (sat, sun):
        ids = [r["student"]["id"] for r in session["roles"]]
        assert len(set(ids)) == len(ids)


def test_four_weekend_sequence_is_fair(client, app):
    """Over four weekends each volunteer of a 3-person job serves before anyone repeats."""
    _, jids = _seed(app, ["Yusuf", "Maryam", "Hana"],
                    {"Mu'adhin": ["Yusuf", "Maryam", "Hana"]})
    j = jids["Mu'adhin"]
    picks = [_who(_get(client, "/api/today", sat)["sessions"][0], j)
             for sat in ("2026-11-07", "2026-11-14", "2026-11-21", "2026-11-28")]
    assert picks[0] == "Yusuf"
    assert set(picks) == {"Yusuf", "Maryam", "Hana"}
    assert all(a != b for a, b in zip(picks, picks[1:]))


def test_adding_volunteer_changes_next_saturday_only(client, app):
    """A volunteer added Wednesday is first next Saturday; past frozen days are untouched."""
    sids, jids = _seed(app, ["Yusuf"], {"Mu'adhin": ["Yusuf"]})
    j = jids["Mu'adhin"]
    _get(client, "/api/today", SAT)
    _get(client, "/api/today", SUN)
    maryam = client.post("/api/students", json={"name": "Maryam"}).get_json()["id"]
    assert client.put(f"/api/jobs/{j}/volunteers?today=2026-11-11",
                      json={"student_ids": [sids["Yusuf"], maryam]}).status_code == 200
    assert _who(_get(client, "/api/today", "2026-11-11")["sessions"][0], j) == "Maryam"
    cal = _get(client, "/api/calendar", "2026-11-11", month="2026-11")
    by_date = {s["date"]: s for s in cal["sessions"]}
    assert _who(by_date[SAT], j) == "Yusuf"
    assert _who(by_date[SUN], j) == "Yusuf"
    assert _who(by_date["2026-11-14"], j) == "Maryam"


def test_manual_override_rules(client, app):
    """Manual accepts volunteers without another role; rejects the rest; returns the session."""
    sids, jids = _seed(app, ["Yusuf", "Maryam", "Hana"],
                       {"Mu'adhin": ["Yusuf", "Maryam"],
                        "Cleaner": ["Yusuf", "Maryam", "Hana"]})
    j1, j2 = jids["Mu'adhin"], jids["Cleaner"]
    r = client.put(f"/api/sessions/2026-11-14/assignments/{j1}?today=2026-11-06",
                   json={"student_id": sids["Hana"]})
    assert r.status_code == 400                      # not a volunteer of Mu'adhin
    r = client.put(f"/api/sessions/2026-11-14/assignments/{j1}?today=2026-11-06",
                   json={"student_id": sids["Yusuf"]})
    assert r.status_code == 200
    role = _role(r.get_json(), j1)
    assert role["student"]["name"] == "Yusuf"
    assert role["source"] == "manual" and role["note"] == "" and role["projected"] is False
    r = client.put(f"/api/sessions/2026-11-14/assignments/{j2}?today=2026-11-06",
                   json={"student_id": sids["Yusuf"]})
    assert r.status_code == 409                      # already has a role that day


def test_clear_assignment(client, app):
    """Clear removes a stored row (today: empty); a projected slot without a row is 404."""
    _, jids = _seed(app, ["Yusuf", "Maryam"], {"Mu'adhin": ["Yusuf", "Maryam"]})
    j = jids["Mu'adhin"]
    _get(client, "/api/today", SAT)
    r = client.delete(f"/api/sessions/{SAT}/assignments/{j}?today={SAT}")
    assert r.status_code == 200
    assert _role(r.get_json(), j) is None
    assert _who(_get(client, "/api/today", SUN)["sessions"][0], j) == "Yusuf"
    with app.app_context():
        assert get_conn().execute(
            "SELECT COUNT(*) c FROM assignments WHERE date = ?", (SAT,)).fetchone()["c"] == 0
    assert client.delete(f"/api/sessions/2026-11-15/assignments/{j}?today={SAT}").status_code == 404


def test_set_start_date(client, app):
    """Start date must be Sat/Sun (400) and not after a frozen session (409)."""
    _seed(app, ["Yusuf"], {"Mu'adhin": ["Yusuf"]})
    assert client.put("/api/settings?today=2026-11-06",
                      json={"start_date": "2026-11-06"}).status_code == 400
    assert client.put("/api/settings?today=2026-11-06",
                      json={"start_date": "banana"}).status_code == 400
    _get(client, "/api/today", SAT)                  # freezes Saturday
    assert client.put("/api/settings?today=2026-11-07",
                      json={"start_date": "2026-11-14"}).status_code == 409
    r = client.put("/api/settings?today=2026-11-07", json={"start_date": "2026-11-07"})
    assert r.status_code == 200 and r.get_json() == {"start_date": "2026-11-07"}


def test_walk_across_dst_weekend(client, app):
    """The 2026-11-01 Sunday (DST fallback) freezes and reads with no off-by-one."""
    _seed(app, ["Yusuf"], {"Mu'adhin": ["Yusuf"]})
    sat = _get(client, "/api/today", "2026-10-31")["sessions"][0]
    assert sat["date"] == "2026-10-31" and sat["weekday"] == "Saturday"
    sun = _get(client, "/api/today", "2026-11-01")["sessions"][0]
    assert sun["date"] == "2026-11-01" and sun["weekday"] == "Sunday"
    assert sun["is_today"] is True
    assert sun["roles"][0]["student"]["name"] == "Yusuf"
    assert sun["roles"][0]["source"] == "auto"
