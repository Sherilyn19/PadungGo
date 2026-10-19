"""Reject oversized request bodies before Django reads them.

Django only checks an uploaded file's size after the whole file has been
received and written to a temporary file. This middleware looks at the
Content-Length header first, so an oversized GTFS upload is refused straight
away. It must run before CsrfViewMiddleware, which reads the request body.

Django never reads more than Content-Length bytes from the request, so a
client cannot get around the limit by sending a smaller header than the real
body.
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse

# Room for the other form fields (title, licence notes, CSRF token, ...).
FORM_FIELDS_ALLOWANCE_BYTES = 1024 * 1024


class UploadSizeLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        max_body = settings.GTFS_UPLOAD_MAX_BYTES + FORM_FIELDS_ALLOWANCE_BYTES
        try:
            declared = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            declared = 0
        if declared > max_body:
            limit_mb = settings.GTFS_UPLOAD_MAX_BYTES // (1024 * 1024)
            return HttpResponse(
                f"Upload too large. The maximum file size is {limit_mb} MB.",
                status=413,
                content_type="text/plain; charset=utf-8",
            )
        return self.get_response(request)
