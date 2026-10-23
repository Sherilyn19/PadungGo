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


def test_health_reports_proxy_counts_but_never_addresses(client, settings):
    settings.TRUSTED_PROXY_HOPS = 2
    resp = client.get("/api/v1/health", HTTP_X_FORWARDED_FOR="203.0.113.5, 198.51.100.7, 10.0.0.1")
    body = resp.json()
    assert body["forwarded_chain_length"] == 3 and body["trusted_proxy_hops"] == 2
    assert "203.0.113.5" not in resp.content.decode() and "198.51.100.7" not in resp.content.decode()


def test_health_chain_length_is_zero_without_the_header(client):
    assert client.get("/api/v1/health").json()["forwarded_chain_length"] == 0
