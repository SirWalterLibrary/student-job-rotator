"""Tests for the read API routes (config, today, calendar, queue)."""
from rotator.app import get_conn

from tests.helpers import make_job, make_students

NOV = ["2026-11-07", "2026-11-08", "2026-11-14", "2026-11-15",
       "2026-11-21", "2026-11-22", "2026-11-28", "2026-11-29"]


def _seed(app) -> None:
    """Give the test database one active student on one active job."""
    with app.app_context():
        conn = get_conn()
        ids = make_students(conn, ["Yusuf"])
        make_job(conn, "Mu'adhin", student_ids=ids)


def _cancel(app, iso_date: str) -> None:
    """Insert a cancelled session row directly."""
    with app.app_context():
        conn = get_conn()
        conn.execute(
            "INSERT INTO sessions (date, status, note) VALUES (?, 'cancelled', 'Teacher away')",
            (iso_date,))
        conn.commit()


def test_config(client):
    """Config reports the (overridden) day, weekday, timezone, pin flag, start_date."""
    body = client.get("/api/config?today=2026-11-06").get_json()
    assert body == {
        "today": "2026-11-06", "weekday": "Friday",
        "timezone": "America/Chicago", "pin_required": False,
        "start_date": "2026-11-07",
    }


def test_today_friday_is_upcoming(client, app):
    """On a Friday, next weekend is shown as two projected sessions."""
    _seed(app)
    body = client.get("/api/today?today=2026-11-06").get_json()
    assert body["today"] == "2026-11-06" and body["weekday"] == "Friday"
    assert body["mode"] == "upcoming" and body["heading"] == "Next weekend"
    assert [s["date"] for s in body["sessions"]] == ["2026-11-07", "2026-11-08"]
    assert all(s["is_today"] is False for s in body["sessions"])
    assert [s["roles"][0]["student"]["name"] for s in body["sessions"]] == ["Yusuf", "Yusuf"]
    assert all(r["projected"] is True for s in body["sessions"] for r in s["roles"])
    assert body["next_held"] is None


def test_today_saturday_is_frozen(client, app):
    """On a Saturday, one session, is_today true, projected false, rows stored."""
    _seed(app)
    body = client.get("/api/today?today=2026-11-07").get_json()
    assert body["mode"] == "today" and body["heading"] == "Today"
    session = body["sessions"][0]
    assert [s["date"] for s in body["sessions"]] == ["2026-11-07"]
    assert session["weekday"] == "Saturday"
    assert session["is_today"] is True and session["status"] == "held"
    assert session["roles"][0]["projected"] is False
    assert body["next_held"] is None
    with app.app_context():
        stored = get_conn().execute(
            "SELECT date, job_id, source FROM assignments WHERE date = '2026-11-07'"
        ).fetchall()
    assert [(r["date"], r["source"]) for r in stored] == [("2026-11-07", "auto")]


def test_today_sunday_is_single_session(client, app):
    """On a Sunday, the single session is Sunday."""
    _seed(app)
    body = client.get("/api/today?today=2026-11-08").get_json()
    assert body["mode"] == "today"
    assert [s["date"] for s in body["sessions"]] == ["2026-11-08"]
    assert body["sessions"][0]["weekday"] == "Sunday"
    assert body["sessions"][0]["is_today"] is True


def test_today_monday_shows_next_weekend(client, app):
    """On a Monday, the weekend shown is the coming one."""
    _seed(app)
    body = client.get("/api/today?today=2026-11-09").get_json()
    assert body["mode"] == "upcoming"
    assert [s["date"] for s in body["sessions"]] == ["2026-11-14", "2026-11-15"]


def test_calendar_november(client, app):
    """The start month shows all 8 sessions with prev null and next December."""
    _seed(app)
    body = client.get("/api/calendar?month=2026-11&today=2026-11-06").get_json()
    assert body["month"] == "2026-11"
    assert body["label"] == "November 2026"
    assert body["prev"] is None
    assert body["next"] == "2026-12"
    assert [s["date"] for s in body["sessions"]] == NOV


def test_calendar_out_of_window_400(client, app):
    """Months before the start month or 25 months out are rejected."""
    assert client.get("/api/calendar?month=2026-10&today=2026-11-06").status_code == 400
    assert client.get("/api/calendar?month=2028-12&today=2026-11-06").status_code == 400


def test_calendar_bad_month_400(client):
    """Garbage month values are rejected."""
    assert client.get("/api/calendar?month=banana&today=2026-11-06").status_code == 400
    assert client.get("/api/calendar?month=2026-13&today=2026-11-06").status_code == 400


def test_calendar_missing_month_uses_current(client, app):
    """Without a month parameter, the current month is used."""
    _seed(app)
    body = client.get("/api/calendar?today=2026-11-06").get_json()
    assert body["month"] == "2026-11"
    assert body["label"] == "November 2026"


def test_api_responses_are_no_store(client):
    """Every /api response carries Cache-Control: no-store."""
    for path in ("/api/health", "/api/config?today=2026-11-06",
                 "/api/today?today=2026-11-06",
                 "/api/calendar?month=2026-11&today=2026-11-06",
                 "/api/queue?today=2026-11-06"):
        assert client.get(path).headers["Cache-Control"] == "no-store", path


def test_today_empty_roster(client):
    """An empty roster still returns sessions, with empty role lists."""
    body = client.get("/api/today?today=2026-11-06").get_json()
    assert len(body["sessions"]) == 2
    assert all(s["roles"] == [] for s in body["sessions"])
    assert body["next_held"] is None


def test_cancelled_saturday_yields_next_held_sunday(client, app):
    """Today = Saturday and cancelled: next_held is Sunday's session view."""
    _seed(app)
    _cancel(app, "2026-11-07")
    body = client.get("/api/today?today=2026-11-07").get_json()
    session = body["sessions"][0]
    assert session["date"] == "2026-11-07"
    assert session["status"] == "cancelled" and session["roles"] == []
    assert body["next_held"] is not None
    assert body["next_held"]["date"] == "2026-11-08"
    assert body["next_held"]["status"] == "held"


def test_friday_with_cancelled_saturday_no_next_held(client, app):
    """Friday with only Saturday cancelled: Sunday is held, next_held is null."""
    _seed(app)
    _cancel(app, "2026-11-07")
    body = client.get("/api/today?today=2026-11-06").get_json()
    assert [s["status"] for s in body["sessions"]] == ["cancelled", "held"]
    assert body["next_held"] is None


def test_queue_lists_jobs_with_turns(client, app):
    """Queue has one entry per active job with the volunteer queue order."""
    _seed(app)
    body = client.get("/api/queue?today=2026-11-06").get_json()
    assert [j["job"]["name"] for j in body["jobs"]] == ["Mu'adhin"]
    entry = body["jobs"][0]
    assert entry["volunteer_count"] == 1
    assert entry["single_volunteer"] is True
    assert entry["queue"] == [
        {"student": {"id": 1, "name": "Yusuf"}, "turns": 0,
         "last_served": "2026-11-07"}]
