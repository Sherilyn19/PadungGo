import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

pytestmark = pytest.mark.django_db
GOOD = "Cebu-Jeep-2026-long"


def _env(monkeypatch, username="padung-go", password=GOOD):
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", username)
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", password)
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")


def test_creates_superuser(monkeypatch):
    _env(monkeypatch)
    call_command("ensure_superuser")
    user = get_user_model().objects.get(username="padung-go")
    assert user.is_superuser and user.is_staff and user.check_password(GOOD)


def test_resets_forgotten_password(monkeypatch):
    get_user_model().objects.create_superuser("padung-go", "a@example.com", "Old-Forgotten-Pass-1")
    _env(monkeypatch)
    call_command("ensure_superuser")
    user = get_user_model().objects.get(username="padung-go")
    assert user.check_password(GOOD)
    assert not user.check_password("Old-Forgotten-Pass-1")


def test_skips_when_unset(monkeypatch):
    monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
    call_command("ensure_superuser")
    assert not get_user_model().objects.exists()


def test_weak_password_rejected_and_not_printed(monkeypatch, capsys):
    _env(monkeypatch, password="123")
    call_command("ensure_superuser")
    assert not get_user_model().objects.exists()
    out = capsys.readouterr()
    assert "123" not in out.out
