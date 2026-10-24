# Security and privacy

The code includes request validation, Django Admin authentication, production host/origin restrictions, secure-cookie settings, upload/archive limits, CSV formula escaping, and request throttles. AI and Geoapify keys are read by the server, not supplied through the public frontend build. These are safeguards, not a security certification.

## Known boundaries

- Default throttles use process-local memory. Multiple workers or replicas do not share a single strict client allowance. Correct trusted-proxy depth is essential; a shared public address can also group unrelated users.
- Endpoint validation is not uniformly strict: plan/explanation top-level fields are checked, but nested origin/destination serializers can ignore unknown keys and coerce numeric values.
- AI output checks reject many unsupported quantities and claims, but cannot prove an explanation correct. Server notices and the deterministic itinerary remain necessary.
- A data status or evidence record does not establish current service, legal boarding access, or a safe walk. Review-date expiry is not automatically enforced.
- `/health` is a deliberately minimal liveness response handled before ordinary host/security middleware; it reveals no database credentials and does not check readiness.

## Location information

There is no application model for persisted commuter journey history. However, selected coordinates reach the API; optional address lookup sends coordinates to Geoapify, and provider-assisted suggestions send search text. Map requests expose the viewed area to the tile service. Search text in GET URLs may appear in infrastructure logs. Provider results may be cached.

The AI provider receives selected public stop names and route facts, without coordinates or typed search text. Those names can still reveal the trip area. Do not describe this as anonymous processing or promise that no infrastructure/provider stores request information.

## Reporting and maintenance

For an ordinary bug without sensitive details, use [repository issues](https://github.com/Sherilyn19/PadungGo/issues). For a vulnerability, use GitHub's private vulnerability-reporting option if enabled; otherwise arrange a private channel with the maintainer before sharing exploit details or credentials. No dedicated security email or response-time commitment is established here.

Keep secrets out of commits, screenshots, logs, and issue reports. If a real secret is exposed, revoke or rotate it; deleting a file alone does not remove history. The October 24 documentation review did not perform a fresh full-history secret scan, dependency vulnerability audit, penetration test, or production backup audit. See [verification results](REVIEW_2026-10-24.md).
