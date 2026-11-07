"""Tests for the ?today= override in request_today()."""
from datetime import date

import pytest

from rotator.app import create_app
from rotator.errors import RotatorError
from rotator.routes_common import request_today


def test_override_ignored_when_disabled(tmp_path):
    """With ALLOW_TODAY_OVERRIDE off, ?today is ignored entirely."""
    app = create_app({"DATA_DIR": str(tmp_path), "ADMIN_PIN": "", "ALLOW_TODAY_OVERRIDE": False})
    from rotator.dates import central_today

    with app.test_request_context("/api/config?today=2026-11-07"):
        assert request_today() == central_today()


def test_override_used_when_enabled(app):
    """With the flag on, a valid ?today is used."""
    with app.test_request_context("/api/config?today=2026-11-07"):
        assert request_today() == date(2026, 11, 7)


def test_override_invalid_400(app):
    """With the flag on, an invalid ?today raises a 400 RotatorError."""
    with app.test_request_context("/api/config?today=11/07/2026"):
        with pytest.raises(RotatorError) as excinfo:
            request_today()
    assert excinfo.value.status == 400
    assert excinfo.value.message == "Invalid today parameter"
