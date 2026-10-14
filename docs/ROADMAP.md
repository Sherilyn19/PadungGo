# Solo Developer Roadmap

**This is a planning target, not proof of registration or a confirmed competition deadline.** The participant reports that organizers clarified that a repository must **not predate October 3, 2026**. Therefore a new repository created after that date is consistent with this stated restriction. Still verify registration, the 20-day submission date, and required October 25 in-person participation.

| Work phase | Required result |
|---|---|
| Repository & route investigation | New GitHub repository; short list of truly interconnected route variants |
| Verified starter dataset | 4-6 connected directional patterns where evidence supports them |
| Django API & database | Structured locations/routes/sources responses and migrations |
| React map & selectors | GPS, search, map pin, and curated location list |
| Trip engine | Direct and one-transfer journey suggestions |
| Journey information | Return alternatives, fare breakdown, walking/waiting/riding estimates as supported |
| Quality & release | Source history, unit tests, README, video demo, deployment |

## Minimum acceptance tests

- Forward-only stop ordering respected, no impossible reversed trip.
- A→B and B→A can recommend **different** patterns.
- A one-transfer trip uses a verifiable and safe transfer connection.
- Unverified routes are excluded from trusted recommendations.
- Fare amounts use a documented rule; travel distance comes from route legs.
- Unknown waiting time is marked unknown.
- GPS permission denial still allows non-GPS location selection.
- No result found is presented clearly rather than substituted with a made-up journey.
