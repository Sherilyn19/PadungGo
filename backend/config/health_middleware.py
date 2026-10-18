"""Answer platform health probes before host validation.

Hosting health checks (e.g. Render) may call the container with an internal
Host header that is not in ALLOWED_HOSTS. This liveness probe returns a static
body only, so it is safe to serve before Django's host check. The full
/api/v1/health view still goes through normal validation.
"""
from django.http import JsonResponse

_BODY = {"status": "ok", "service": "padunggo-backend"}


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health" and request.method in ("GET", "HEAD"):
            return JsonResponse(_BODY)
        return self.get_response(request)
