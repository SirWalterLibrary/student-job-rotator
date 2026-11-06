"""Tests for the app factory, config and basic routing."""
import pytest

from rotator.app import create_app


def test_health_ok(client):
    """GET /api/health returns 200 with {"ok": true}."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_index_served(client):
    """GET / serves the placeholder index.html."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Khidmah Roster" in resp.get_data(as_text=True)


def test_unknown_api_route_is_json_404(client):
    """An unknown /api/ route returns a JSON 404."""
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Not found"}


def test_production_requires_pin(tmp_path):
    """APP_ENV=production refuses to start with an empty PIN, accepts it with one."""
    base = {"DATA_DIR": str(tmp_path), "APP_ENV": "production"}
    with pytest.raises(RuntimeError):
        create_app({**base, "ADMIN_PIN": ""})
    app = create_app({**base, "ADMIN_PIN": "1234"})
    assert app is not None


def test_api_responses_not_cached(client):
    """/api responses carry Cache-Control: no-store."""
    resp = client.get("/api/health")
    assert resp.headers.get("Cache-Control") == "no-store"
