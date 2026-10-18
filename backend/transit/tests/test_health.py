"""Health endpoint and basic config tests."""
import pytest
from django.test import Client


@pytest.mark.parametrize("url", ["/health", "/api/v1/health"])
def test_health_ok(url):
    client = Client()
    resp = client.get(url)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "padunggo-backend"
    # No secrets leaked.
    assert "SECRET" not in str(body).upper()
    assert "password" not in str(body).lower()


def test_settings_lite_mode():
    from django.conf import settings

    assert settings.GIS_ENABLED is False  # test suite runs in lite mode
