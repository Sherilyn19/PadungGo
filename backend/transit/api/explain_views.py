"""POST /journeys/explain: an AI-written explanation of one planned trip.

The browser sends the search it already made plus the IDs of the chosen rides.
This view plans again, finds that exact trip in the planner's own output, and
gives only that trip's facts to the AI. Provider problems return 200 with
status "unavailable" (like the place endpoints), because the app works fine
without an explanation; the planner itself is never involved in those failures.
"""
from __future__ import annotations

from datetime import date

from rest_framework import status as http_status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from transit.ai.explainer import explain_trip
from transit.planner import PlanRequest, plan_journeys
from transit.planner.engine import PlannerError
from transit.planner.loader import load_network
from transit.planner.validation import MAX_JOURNEY_OPTIONS

from .errors import error_response
from .serializers import ExplainRequestSerializer
from .throttles import ExplainRateThrottle, GeneralRateThrottle
from .views import _planner_config, _resolve_endpoint, _UnresolvableLocation

# Plain-language text for each reason, and whether trying again can help.
UNAVAILABLE = {
    "not_configured": ("AI explanations are not available right now.", False),
    "quota": ("AI explanations have reached today's limit. Please try again tomorrow.", False),
    "rate_limited": ("The AI service is busy. Please try again in a minute.", True),
    "timeout": ("The AI service took too long to answer. Please try again.", True),
    "error": ("The AI service could not be reached. Please try again.", True),
    "invalid_output": ("The AI answer did not pass our accuracy checks, so it is not shown. Please try again.", True),
}


def _ride_key(ride: dict) -> tuple[str, str, str]:
    """Identity of one ride: which pattern, boarded and left at which stop visits."""
    return (str(ride["route_pattern_id"]), str(ride["board_occurrence_id"]), str(ride["alight_occurrence_id"]))


def _find_option(options: list[dict], rides: list[dict]) -> dict | None:
    wanted = [_ride_key(ride) for ride in rides]
    for option in options:
        if [_ride_key(s) for s in option["segments"] if s["mode"] == "ride"] == wanted:
            return option
    return None


def _unavailable_response(reason: str, check: str | None = None) -> Response:
    message, retryable = UNAVAILABLE.get(reason, UNAVAILABLE["error"])
    body = {"status": "unavailable", "reason": reason, "message": message, "retryable": retryable}
    if check:
        # A short code such as "missing_stop_name": which accuracy check failed. Never answer text.
        body["check"] = check
    return Response(body)


@api_view(["POST"])
# This decorator replaces the defaults, so keep the general per-visitor limit.
@throttle_classes([GeneralRateThrottle, ExplainRateThrottle])
def explain_journey(request):
    serializer = ExplainRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        origin = _resolve_endpoint(data["origin"])
        destination = _resolve_endpoint(data["destination"])
    except _UnresolvableLocation as exc:
        return error_response("invalid_request", str(exc), http=http_status.HTTP_400_BAD_REQUEST,
                              fields={"location_id": [str(exc)]})

    # Same inputs as the visitor's search: the trip must come from the planner.
    plan_request = PlanRequest(
        origin=origin, destination=destination, max_transfers=data["max_transfers"],
        limit=MAX_JOURNEY_OPTIONS, sort_by=data["sort_by"], query_date=date.today(),
    )
    config = _planner_config()
    network = load_network(allow_documented=config["ALLOW_DOCUMENTED"])
    try:
        plan = plan_journeys(network, plan_request, config=config)
    except PlannerError as exc:
        return error_response("invalid_request", str(exc), http=http_status.HTTP_400_BAD_REQUEST)

    option = _find_option(plan.journey_options, data["rides"])
    if option is None:
        return error_response(
            "not_found", "That trip is no longer available. Please search again.",
            http=http_status.HTTP_404_NOT_FOUND,
        )

    explanation = explain_trip(option)
    if explanation.status != "ok":
        return _unavailable_response(explanation.reason, explanation.check)
    return Response({
        "status": "ok",
        "explanation": explanation.text,
        "notices": list(explanation.notices),
        "ai_generated": True,
        "model": explanation.model,
    })
