"""Tests for the admin PIN guard, rate limiting, and POST /api/auth."""
import pytest

from rotator import auth
from rotator.app import create_app

PIN = "1234"
PIN_HEADERS = {"X-Admin-Pin": PIN}


@pytest.fixture
def pin_app(tmp_path, monkeypatch):
    """A test app with a PIN plus a fresh limiter on a fake (injectable) clock."""
    app = create_app(
        {
            "DATA_DIR": str(tmp_path),
            "ADMIN_PIN": PIN,
            "ALLOW_TODAY_OVERRIDE": True,
        }
    )
    clock = {"t": 0.0}
    monkeypatch.setattr(auth, "_DEFAULT_LIMITER",
                        auth.FailureLimiter(max_failures=5, window_seconds=60, now=lambda: clock["t"]))
    return app, clock


@pytest.fixture(autouse=True)
def _clean_limiter():
    """Each test starts with no recorded failures."""
    auth.limiter().reset("127.0.0.1")


def test_mutating_requires_pin(pin_app):
    """Mutating route: no header 401, wrong 401, right 201; GET /api/today needs none."""
    client = pin_app[0].test_client()
    resp = client.post("/api/students", json={"name": "Yusuf"})
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "Teacher PIN required"}

    resp = client.post("/api/students", json={"name": "Yusuf"},
                       headers={"X-Admin-Pin": "9999"})
    assert resp.status_code == 401

    resp = client.post("/api/students", json={"name": "Yusuf"}, headers=PIN_HEADERS)
    assert resp.status_code == 201

    assert client.get("/api/today").status_code == 200
    assert client.get("/api/config").status_code == 200
    assert client.get("/api/config").get_json()["pin_required"] is True


def test_no_pin_configured_is_open(client):
    """With no PIN set, mutating routes work without the header."""
    resp = client.post("/api/students", json={"name": "Yusuf"})
    assert resp.status_code == 201
    assert client.get("/api/config").get_json()["pin_required"] is False


def test_pin_check_endpoint(pin_app):
    """POST /api/auth: 400 without pin, 401 wrong, 200 right."""
    client = pin_app[0].test_client()
    assert client.post("/api/auth").status_code == 400
    assert client.post("/api/auth", json={"pin": "9999"}).status_code == 401
    resp = client.post("/api/auth", json={"pin": PIN})
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_pin_check_without_pin_always_ok(client):
    """No PIN configured: POST /api/auth is ok no matter what."""
    assert client.post("/api/auth", json={"pin": ""}).status_code == 200
    assert client.post("/api/auth", json={"pin": "x"}).status_code == 200


def test_five_wrong_pins_then_blocked(pin_app):
    """5 wrong PINs in a minute → 429 (even with the right PIN); the window then clears."""
    app, clock = pin_app
    client = app.test_client()
    for _ in range(5):
        assert client.post("/api/auth", json={"pin": "9999"}).status_code == 401

    resp = client.post("/api/auth", json={"pin": PIN})
    assert resp.status_code == 429
    resp = client.post("/api/students", json={"name": "Yusuf"}, headers=PIN_HEADERS)
    assert resp.status_code == 429

    clock["t"] += 61
    assert client.post("/api/auth", json={"pin": PIN}).status_code == 200
    resp = client.post("/api/students", json={"name": "Yusuf"}, headers=PIN_HEADERS)
    assert resp.status_code == 201


def test_pin_comparison_is_constant_time():
    """auth.py compares PINs with hmac.compare_digest."""
    import pathlib

    source = pathlib.Path(auth.__file__).read_text()
    assert "hmac.compare_digest" in source


def test_pin_ok_direct():
    """pin_ok: matches the configured PIN, rejects others, open when unset."""
    assert auth.pin_ok({"ADMIN_PIN": PIN}, PIN)
    assert not auth.pin_ok({"ADMIN_PIN": PIN}, "9999")
    assert auth.pin_ok({"ADMIN_PIN": ""}, "")
    assert auth.pin_ok({"ADMIN_PIN": ""}, "anything")
