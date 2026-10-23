"""Per-visitor request limits for endpoints that are expensive or use a paid quota."""
from rest_framework.throttling import AnonRateThrottle


class PlanRateThrottle(AnonRateThrottle):
    """Trip planning. Rate comes from DRF_PLAN_THROTTLE (default 30/min)."""

    scope = "plan"


class PlacesRateThrottle(AnonRateThrottle):
    """Place suggestions and addresses. Rate comes from DRF_PLACES_THROTTLE (default 40/min)."""

    scope = "places"
