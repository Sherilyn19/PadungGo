"""Journey identity, stable ranking, and supported comparison labels."""
from __future__ import annotations


def journey_key(segments: list[dict]) -> tuple:
    key = []
    for segment in segments:
        if segment["mode"] == "ride":
            key.append((
                "ride",
                segment["route_pattern_id"],
                segment["board_occurrence_id"],
                segment["alight_occurrence_id"],
            ))
        elif segment["mode"] == "transfer_walk":
            key.append((
                "transfer",
                segment.get("from_stop_id"),
                segment.get("to_stop_id"),
            ))
    return tuple(key)


def deduplicate_options(options: list[dict]) -> list[dict]:
    """Keep the first option for each ordered ride-and-transfer identity."""
    seen = {}
    for option in options:
        key = option["_dedup_key"]
        if key not in seen:
            seen[key] = option
    return list(seen.values())


def _fewest_transfers_key(option: dict) -> tuple:
    # Shorter road distance breaks transfer-count ties to avoid long loops.
    return (
        option["transfers"],
        option["_ride_m"],
        option["_walk_known_m"],
        option["_dedup_key"],
    )


def rank_options(options: list[dict], sort_by: str) -> tuple[list[dict], dict]:
    """Sort in place, disclosing fallback when totals cannot be compared."""
    applied = sort_by
    warning = None

    if sort_by == "cheapest":
        comparable = [o for o in options if o["fare"]["total_is_complete"]]
        if len(comparable) == len(options) and options:
            options.sort(key=lambda o: (o["fare"]["total_centavos"], o["transfers"], o["_dedup_key"]))
        else:
            applied = "fewest_transfers"
            warning = "Cannot fairly rank by cheapest: some fares are unknown. Fell back to fewest_transfers."
            options.sort(key=_fewest_transfers_key)
    elif sort_by == "fastest":
        comparable = [o for o in options if o["time"]["total_is_complete"]]
        if len(comparable) == len(options) and options:
            options.sort(key=lambda o: (o["time"]["total_seconds"], o["transfers"], o["_dedup_key"]))
        else:
            applied = "fewest_transfers"
            warning = "Cannot fairly rank by fastest: some durations are unknown. Fell back to fewest_transfers."
            options.sort(key=_fewest_transfers_key)
    elif sort_by == "least_walking":
        # Straight-line estimates cannot establish the shortest walkable route.
        applied = "fewest_transfers"
        warning = "Cannot fairly rank by least_walking: walking distances are approximate. Fell back to fewest_transfers."
        options.sort(key=_fewest_transfers_key)
    else:
        options.sort(key=_fewest_transfers_key)

    ranking = {"requested": sort_by, "applied": applied, "warning": warning}
    return options, ranking


def apply_labels(options: list[dict]) -> None:
    """Label the returned options using only supported comparisons."""
    if not options:
        return
    minimum_transfers = min(o["transfers"] for o in options)
    for option in options:
        if option["transfers"] == minimum_transfers:
            option["labels"].append("fewest_transfers")

    complete_fares = [o for o in options if o["fare"]["total_is_complete"]]
    if complete_fares:
        cheapest = min(o["fare"]["total_centavos"] for o in complete_fares)
        for option in complete_fares:
            if option["fare"]["total_centavos"] == cheapest:
                option["labels"].append("cheapest")

    complete_times = [o for o in options if o["time"]["total_is_complete"]]
    if complete_times:
        fastest = min(o["time"]["total_seconds"] for o in complete_times)
        for option in complete_times:
            if option["time"]["total_seconds"] == fastest:
                option["labels"].append("fastest")