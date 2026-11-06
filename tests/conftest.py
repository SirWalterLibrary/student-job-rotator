"""Shared pytest fixtures for the Khidmah Roster tests."""
import pytest

from rotator.app import create_app


@pytest.fixture
def app(tmp_path):
    """A test app pointed at a throwaway data directory."""
    return create_app(
        {
            "DATA_DIR": str(tmp_path),
            "ADMIN_PIN": "",
            "ALLOW_TODAY_OVERRIDE": True,
        }
    )


@pytest.fixture
def client(app):
    """A test client for the app fixture."""
    return app.test_client()
