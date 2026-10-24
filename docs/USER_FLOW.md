# Using PadungGo

Open [PadungGo](https://padung-go.app). A short welcome screen appears on page load; it is timed and does not mean the API is ready.

1. Select your start and destination. Type a place and choose a suggestion, use device location with permission, or select a point on the map. Check the marker: similarly named places may be different locations.
2. Search for journeys. The hosted API may take time to wake. Available results contain direct rides or one transfer; use the control below the list to reveal more alternatives.
3. Open an option. Read the numbered walking, boarding, transfer, and alighting steps, and compare the ride line with the map.
4. Review the fare information. Choose Regular or the grouped Student/Senior/PWD category and a vehicle type per ride. “Not sure” can show a range. These are estimates, not a guarantee of entitlement, vehicle type, or the amount collected. If any ride lacks a usable amount, a complete total is not shown.
5. Optionally press **Explain this trip**. The AI-generated text summarizes the selected itinerary. Read the “Before you go” notices and the original trip details. AI explanations do not use your fare-selector choices and may leave the fare unknown even when the interface displays an estimate.
6. Use the return-trip action for a fresh search. The return service and stops may differ or may be missing.

## Read the uncertainty labels

- **Historic / not field-verified:** the source does not confirm current operation. Confirm locally before relying on it.
- **Scarce:** reports suggest few vehicles. No measured wait is available. An unflagged route is not confirmed frequent.
- **Estimated / approximate fare:** recorded distance and vehicle assumptions can differ from actual charging. Ask the driver.
- **Unknown time:** the application lacks a supported duration. An archived ride subtotal is not a full trip time.
- **Walking connection:** dashed straight lines are not checked walking paths. Use safe, permitted crossings.

The data-update date means stored network information changed; it is not the date someone rode every route.

## When something is unavailable

| Situation | Meaning and action |
|---|---|
| No journey found | The stored data and one-transfer search cannot supply an option. This does not prove no public transport exists. Try a nearby known landmark or ask locally. |
| Start and destination are almost identical | Choose distinct endpoints if you intended a ride. |
| Address unavailable | The selected coordinates are still used. Check the pin before searching. |
| AI explanation unavailable | Continue using the itinerary. The provider, quota, or output checks may have prevented an answer. |
| Too many requests | Wait for the indicated retry period. |
| A route looks wrong | Do not rely on it. [Report an issue](https://github.com/Sherilyn19/PadungGo/issues) with a source and observation date, without private trip history. |

See the [source register](DATA_SOURCES.md) for provenance and the [project overview](../README.md) for scope.
