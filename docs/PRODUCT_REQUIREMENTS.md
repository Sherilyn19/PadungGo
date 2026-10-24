# Current capabilities and scope

PadungGo helps commuters understand possible public-transport journeys in Metro Cebu. Its intended area is Cebu City, Mandaue City, and Lapu-Lapu City; the actual stored network is incomplete and mostly historical.

| Capability | Current implementation and limits |
|---|---|
| Choose places | Stored names, aliases, and acronyms; optional Geoapify suggestions; device position or map pin |
| Plan a journey | Direct or one-transfer options using eligible stored directional patterns |
| Compare alternatives | Fewest-transfers interface; scarce services grouped last; up to 50 requested options, displayed eight at a time |
| Understand the trip | Boarding, alighting, transfer steps, and ride geometry; straight walking connections |
| Check the return | A separate search with reversed endpoints, not a reversed outbound itinerary |
| Estimate fares | Distance-based guide estimates and available evidence-supported quotes; passenger/vehicle choices in the interface |
| Understand uncertainty | Historic-data, scarcity, unknown fare/time, and approximate-walk notices |
| Explain the trip | Optional AI summary, checked by the backend, with server-written notices |
| Maintain data | Authenticated Django Admin, evidence records, GTFS import, selected OpenStreetMap imports and preview actions |

The API accepts four sorting choices, but cheaper/faster options require sufficient comparable data and otherwise fall back to fewest transfers. Least walking currently falls back. The interface hides the sort selector while the usable ordering is fewest transfers.

## Product boundaries

The current version has no live vehicle tracking, guaranteed service availability, ticketing, booking, complete travel-time estimate, offline routing, or full regional coverage. The planner does not enforce an exact city polygon. Search is a bounded heuristic, not proof that no other journey exists.

A stored verification label is a maintained data status, not automatic proof of freshness. Review dates do not automatically expire eligibility. AI does not find routes or establish fares; the frontend's passenger and vehicle choices are not included in its summary request.

See [user instructions](USER_FLOW.md), [routing behavior](ROUTING_ALGORITHM.md), and [future work](ROADMAP.md).
