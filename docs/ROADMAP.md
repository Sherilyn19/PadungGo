# Roadmap

These are future priorities, not promises of implemented functionality or a committed schedule. See [current capabilities](PRODUCT_REQUIREMENTS.md) and [verification results](IMPLEMENTATION_REVIEW.md) first.

| Priority | Improvement | Evidence needed before claiming completion |
|---|---|---|
| Data rights | Establish historical feed reuse/redistribution permissions or replace it with suitably licensed data | Source-specific terms or permission and attribution record |
| Current service | Verify directional routes, boarding places, transfer access, and unresolved Mandaue corrections | Dated observations/operator evidence and reviewed geometry |
| Fare reliability | Resolve vehicle subtype, fractional-distance treatment, source applicability, and guide supersession | Applicable current source and regression examples |
| Consistent explanation | Align AI facts with selected passenger/vehicle estimates while preserving estimate labels | Contract changes and tests across known/unknown fares |
| Freshness | Enforce review expiry and improve source/observation-date presentation | Explicit policy, eligibility checks, and tests |
| Search quality | Assess nearest-stop heuristics, coverage boundaries, additional transfers and alternatives | Representative journeys, correctness comparisons, and performance measurements |
| Operations | Shared caches/client limits, readiness checks, restore testing and observability | Multi-worker/replica checks and operational evidence |
| Quality | Browser journeys, accessibility review, PostGIS integration tests and bundle reduction | Repeatable checks and measured before/after results |

More routes, live arrivals, complete journey times, offline use, and ticketing are not present capabilities. Expand only when suitable data, permissions, and testing support the claim.
