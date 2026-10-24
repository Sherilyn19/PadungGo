# Historical demonstration audit: 17D → 42D

Recorded October 20, 2026. **Retired as a current demonstration:** 42D was subsequently excluded from suggestions. See [availability decisions](ROUTE_AVAILABILITY_2026-10.md). The record below preserves historical identifiers, geometry/duration provenance, and shared-stop implications; it is not current travel advice or a reproducible promise of today's results.

The audit used [desktop research](RESEARCH_17D_42D_2026-10-20.md) and a read-only production API request. It did not field-verify service or directly change production data. Database-query details below were supplied separately by a maintainer.

## 1. The journey as the API returns it

At the time of the audit, the request below reproduced Option 1 (the origin is moved next to stop 2939, so the first walk is about 6 m instead of the demo's ~229 m):

```json
{"origin":{"latitude":10.32263,"longitude":123.89862},
 "destination":{"location_id":"51ce03c5-3e71-467b-a938-c46911558cfb"},
 "sort_by":"fewest_transfers","max_transfers":1,"limit":5}
```

| Leg | Record | Value from the API |
|---|---|---|
| Ride 1 | Route 17D | `dfae67a9-42e5-4e52-9f48-e9e536c71f59`, name `APAS - LAHUG - CARBON via Escario`, vehicle_class `jeepney`, operator `Department of Transportation, Cebu (DOTC)` |
| | Pattern | `704fc96e-2505-462c-9499-8b24ef20fbf8`, direction `unspecified`, signboard empty, status `documented` |
| | Board | occurrence `2d53ea54-8d30-4ad5-99f5-587e31ee28d6` (sequence 10), "Unnamed stop (feed id 2939)", 10.322633, 123.898678 |
| | Alight | occurrence `1beace6b-c925-4b7f-951e-fc5f6b26e8ae` (sequence 23), "Sanciangko", 10.296654, 123.893616 |
| | Distance / time | 4,055 m along the archived shape; 644 s from the archived schedule |
| Transfer | TransferConnection | from and to the **same** stop `b059f6e0-5b9a-4df7-a7e3-fcabe1b7121b` (Sanciangko), 0 m, no duration |
| Ride 2 | Route 42D | `52710e90-0b14-4c19-8f59-bf872927d2d4`, name `Name missing`, vehicle_class `jeepney`, same operator |
| | Pattern | `f7592fc3-21e4-41dd-9977-405cfb4040cc`, direction `unspecified`, signboard empty, status `documented` |
| | Board | occurrence `d7431581-ca0e-4b60-b400-4d613942978b` (sequence 43), Sanciangko (stop `b059f6e0…`) |
| | Alight | occurrence `327d5610-4691-4555-a3dc-226b5925b224` (sequence 72), "Cebu South Road", 10.28237, 123.857947 |
| | Distance / time | 4,443 m along the archived shape; 524 s from the archived schedule |
| Final walk | | 452.5 m in a straight line to the location "Cebu South Road & A Gabuya Street" (10.279336, 123.855191) |
| Source | DataSource | `929f1131-6577-4ced-95fa-0d3d55850b0b`, "Cebu DOTC GTFS (Transitland archive)", published date empty, **license empty** |
| Fare rules | | None applied (`rule_id: null` on both legs) |

Stop IDs, from a maintainer-supplied read-only Supabase query on 2026-10-20:

| Stop | Stop ID | Other patterns using the same record |
|---|---|---|
| Unnamed stop (feed id 2939) | `7c12b541-1651-409f-bd0c-6da304b0ad50` | 11 patterns: 03D, 04C, 04D, 04E, 04I, 04L, 17B, 17C, 17D, 51E, 60 |
| Sanciangko (transfer) | `b059f6e0-5b9a-4df7-a7e3-fcabe1b7121b` | 30 patterns, including 17C, 17D, 42D, 43, 51E, 64C and the 02/04/09/10/12/13 series |
| Cebu South Road (42D exit) | `22d44f9b-5da3-4684-a28a-f7e0c4e6f80c` | 10C, 10E, 10J, 10K, 10M, 10O, 41D, 42D (twice: seq 8 and 72), 43 |

Renaming any of these records changes the name for every pattern listed.

## Interpretation

The ride distances and durations came from archived geometry and schedules. The transfer used a shared physical stop, not a field-verified pedestrian connection. No fare rule applied in this historical response, and the source license field was empty.

Subsequent guide estimates are a separate feature; see [fare evidence](FARE_GUIDE_2026-09-28.md). The source-permission and current-operation gaps remain distinct from successful routing. Shared stop edits can affect many patterns, so review identity and source scope before changing a name or access flag.
