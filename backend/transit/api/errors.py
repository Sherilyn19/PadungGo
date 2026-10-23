"""Uniform error envelope per docs/API_DESIGN.md: {error:{code,message,...}}."""
from __future__ import annotations

from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def error_response(code: str, message: str, *, http: int, fields=None, retryable: bool = False) -> Response:
    body = {"error": {"code": code, "message": message, "retryable": retryable}}
    if fields:
        body["error"]["fields"] = fields
    return Response(body, status=http)


def exception_handler(exc, context):
    """Wrap DRF errors in the canonical envelope with safe messages."""
    response = drf_exception_handler(exc, context)
    if response is None:
        # Unhandled -> safe 503, never leak raw DB/provider exceptions.
        return error_response(
            "service_unavailable",
            "The service could not produce a trustworthy answer. Please retry.",
            http=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
        )

    code_map = {
        400: "invalid_request",
        404: "not_found",
        405: "invalid_request",
        429: "rate_limited",
        503: "service_unavailable",
    }
    code = code_map.get(response.status_code, "error")
    detail = response.data
    message = "Invalid request."
    fields = None
    if isinstance(detail, dict):
        if "detail" in detail:
            message = str(detail["detail"])
        else:
            fields = {k: [str(v) for v in (vs if isinstance(vs, list) else [vs])] for k, vs in detail.items()}
            message = "One or more fields are invalid."
    elif isinstance(detail, list):
        message = "; ".join(str(d) for d in detail)

    if response.status_code == 429:
        # DRF's own wording ("Request was throttled. Expected available in N seconds.") is technical.
        message = "You have searched a lot in a short time. Please wait a minute, then try again."
    retryable = response.status_code in (429, 503)
    new = error_response(code, message, http=response.status_code, fields=fields, retryable=retryable)
    if "Retry-After" in response.headers:
        new.headers["Retry-After"] = response.headers["Retry-After"]
    return new
