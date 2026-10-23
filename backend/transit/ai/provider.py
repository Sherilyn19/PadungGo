"""Server-side client for an OpenAI-compatible chat-completions endpoint.

Built on the standard library, so no new dependency is added. The API key is
sent only in a request header, from this server; the browser never sees it.

Privacy: nothing here logs prompts, trip facts, model output, URLs or the key.
Failures are logged as an HTTP status number only.

Quota: each call first takes one unit from a shared daily counter (stored in
the database, so every web worker and restart agrees). That keeps the app
inside the provider's free-plan limit.
"""
from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

from transit.models import ProviderUsage

logger = logging.getLogger(__name__)

PROVIDER = "ai"
USER_AGENT = "PadungGo/1.0 (+https://padung-go.vercel.app)"
RATE_LIMIT_PAUSE_SECONDS = 30
REJECTED_KEY_PAUSE_SECONDS = 10 * 60
MAX_RESPONSE_BYTES = 64 * 1024
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1"})


@dataclass
class Completion:
    # ok | not_configured | quota | rate_limited | timeout | error | invalid_output
    status: str
    text: str = ""


def _config() -> dict:
    return settings.AI


def is_configured() -> bool:
    """True only when a key, model and a safe endpoint URL are all set."""
    config = _config()
    if not (config["API_KEY"] and config["MODEL"] and config["BASE_URL"]):
        return False
    parts = urllib.parse.urlparse(config["BASE_URL"])
    if parts.scheme == "https" and parts.hostname:
        return True
    # Plain HTTP is allowed only for a local test server during development.
    return bool(settings.DEBUG and parts.scheme == "http" and parts.hostname in LOCAL_HOSTS)


def _reserve_request() -> bool:
    """Count one call against today's (UTC) limit; False when it is used up."""
    limit = _config()["DAILY_REQUEST_LIMIT"]
    if limit <= 0:
        return False
    today = timezone.now().date()
    ProviderUsage.objects.get_or_create(provider=PROVIDER, day=today)
    # One conditional UPDATE, so two workers cannot both take the last unit.
    updated = (ProviderUsage.objects
               .filter(provider=PROVIDER, day=today, requests__lt=limit)
               .update(requests=F("requests") + 1))
    return updated == 1


def _pause(status: str, seconds: int) -> None:
    cache.set(f"{PROVIDER}:paused", status, seconds)


def _request_body(messages: list[dict]) -> bytes:
    config = _config()
    payload = {
        "model": config["MODEL"],
        "messages": messages,
        "temperature": 0.2,
        "max_completion_tokens": config["MAX_OUTPUT_TOKENS"],
    }
    if config["REASONING_EFFORT"]:
        payload["reasoning_effort"] = config["REASONING_EFFORT"]
    return json.dumps(payload).encode()


def _read_text(response) -> Completion:
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        return Completion("error")
    try:
        choice = json.loads(raw)["choices"][0]
        text = choice["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return Completion("error")
    # A reply cut off by the token limit may end mid-sentence, so it is not used.
    if choice.get("finish_reason") == "length" or not isinstance(text, str):
        return Completion("invalid_output")
    return Completion("ok", text)


def _http_error(exc: urllib.error.HTTPError) -> Completion:
    if exc.code == 429:
        _pause("rate_limited", RATE_LIMIT_PAUSE_SECONDS)
        return Completion("rate_limited")
    if exc.code in (401, 403):
        logger.warning("AI provider rejected the API key (HTTP %s).", exc.code)
        _pause("error", REJECTED_KEY_PAUSE_SECONDS)
    else:
        logger.warning("AI provider returned HTTP %s.", exc.code)
    return Completion("error")


def request_completion(messages: list[dict]) -> Completion:
    """Ask the model once. Never raises for provider problems."""
    if not is_configured():
        return Completion("not_configured")
    paused = cache.get(f"{PROVIDER}:paused")
    if paused:
        return Completion(paused)
    if not _reserve_request():
        return Completion("quota")

    config = _config()
    request = urllib.request.Request(
        f"{config['BASE_URL']}/chat/completions",
        data=_request_body(messages),
        headers={
            "Authorization": f"Bearer {config['API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config["TIMEOUT_SECONDS"]) as response:
            return _read_text(response)
    except urllib.error.HTTPError as exc:
        return _http_error(exc)
    except (TimeoutError, socket.timeout):
        return Completion("timeout")
    except urllib.error.URLError as exc:
        timed_out = isinstance(exc.reason, (TimeoutError, socket.timeout))
        return Completion("timeout" if timed_out else "error")
    except (ValueError, OSError):
        return Completion("error")
