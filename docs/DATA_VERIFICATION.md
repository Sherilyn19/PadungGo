# Transport data verification

Historic route records, map geometry, and current service observations answer different questions. Preserve their dates, scope, and uncertainty instead of treating a recent webpage retrieval as proof of current operation.

## Review before calling guidance verified

1. Confirm route identity, operator, vehicle class, and variants.
2. Establish current operation with dated, credible evidence.
3. Review each direction separately, including streets and stop order.
4. Confirm boarding/alighting permission and directed transfer access, including pedestrian safety.
5. Check fare applicability, effective dates, distance treatment, discounts, and rounding separately. Unsupported fares stay unknown.
6. Record publisher, reference, observation/review dates, reviewer, scope, and conflicting evidence.
7. Establish rights to import, display, derive from, and redistribute each source as applicable.

These are contributor review standards. The application does not automatically prove every item merely because a record is marked verified.

## Stored statuses and actual use

| Status | Meaning | Planner use |
|---|---|---|
| `candidate` | Research lead | Excluded |
| `documented` | Published evidence; current operation not established | Excluded by default; admitted when documented mode is enabled |
| `verified` | Maintainer-reviewed supporting evidence | Eligible, subject to other access/route checks |
| `needs_review` | Disputed, stale, or incomplete evidence | Excluded |

The configured deployment enables documented mode for the historic network and displays notices. It should not be described as a fully verified current network. An active Route flag only controls inclusion; “not flagged” availability does not prove frequent service.

Review dates do not automatically expire eligibility. Maintainers must act on stale or conflicting evidence. A source-level license field is metadata, not automatic legal permission. Supported fare quotations perform additional scope/evidence checks; separate guide estimates remain approximate.

## Evidence record template

```text
Route record and code / place:
Operator and vehicle subtype:
Direction and variant:
Ordered streets, stops, terminals and access:
Source title / publisher / reference:
Publication date / observation date:
Geometry and distance provenance:
License or permission and its scope:
Fare applicability and effective dates:
Conflicting or missing evidence:
Reviewer / review date / next review:
Status and reason:
```

Do not publish identifying passenger information, private trip histories, unredacted plates, or restricted source assets. A sighting can support a service report without supplying an entire navigable route. Shared stop-name changes affect every pattern using the same physical record.

Use [the source register](DATA_SOURCES.md), [availability decisions](ROUTE_AVAILABILITY_2026-10.md), and [fare evidence](FARE_GUIDE_2026-09-28.md). Historical 01K, 23D, 20A, and 03Q research was an initial batch, not a permanent network boundary or proof of coverage.
