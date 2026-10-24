"""Eligible stops and directed direct/one-transfer journey enumeration."""
from __future__ import annotations

from datetime import date
from typing import Iterator, Optional

from .assembly import assemble_direct_option, assemble_transfer_option
from .geo import haversine_m
from .journey_types import (
    Endpoint,
    Network,
    PatternData,
    PatternStopData,
    PlanRequest,
    TransferData,
)
from .search_types import (
    OccurrenceIndex,
    RideLeg,
    SearchContext,
    StopCandidate,
    TransferCandidate,
)

MAX_TRANSFER_CANDIDATES = 40
# A ride that ends within a short walk of where it began is a loop, not a trip: nobody
# rides 15 km around a loop to get 300 m. Walking is allowed in this planner, so such
# rides are not offered. Both limits must hold: short straight-line gap, long ride.
LOOP_WALK_M = 1000
LOOP_MIN_RIDE_M = 3000
LOOP_RATIO = 3


def is_loop_ride(network: Network, board: PatternStopData, alight: PatternStopData) -> bool:
    """True if riding from `board` to `alight` only brings the passenger back to where they started."""
    ride_m = alight.distance_along_m - board.distance_along_m
    start, end = network.stops.get(board.stop_id), network.stops.get(alight.stop_id)
    if start is None or end is None:
        return False
    straight = haversine_m(start.latitude, start.longitude, end.latitude, end.longitude)
    return straight < LOOP_WALK_M and ride_m > max(LOOP_MIN_RIDE_M, LOOP_RATIO * straight)


def _eligible_stops(
    network: Network, endpoint: Endpoint, *, radius_m: float, boarding: bool,
    allowed_statuses: frozenset[str],
) -> list[StopCandidate]:
    """Find nearby eligible stops; straight-line distance is only a filter."""
    candidates = []
    for stop in network.stops.values():
        if stop.status not in allowed_statuses:
            continue
        if boarding and not stop.can_board:
            continue
        if not boarding and not stop.can_alight:
            continue
        distance = haversine_m(
            endpoint.latitude, endpoint.longitude, stop.latitude, stop.longitude,
        )
        if distance <= radius_m:
            candidates.append(StopCandidate(stop.id, distance))
    candidates.sort(key=lambda candidate: (candidate.straight_line_m, candidate.stop_id))
    return candidates


# Reported distances are rounded: they are a hint about coverage, not a measured walk.
_COVERAGE_ROUNDING_M = 100


def nearest_stop_distance_m(
    network: Network, endpoint: Endpoint, *, boarding: bool, allowed_statuses: frozenset[str],
) -> Optional[int]:
    """Straight-line metres to the closest eligible stop at any distance, or None if there is none."""
    nearest = None
    for stop in network.stops.values():
        if stop.status not in allowed_statuses:
            continue
        if not (stop.can_board if boarding else stop.can_alight):
            continue
        distance = haversine_m(endpoint.latitude, endpoint.longitude, stop.latitude, stop.longitude)
        if nearest is None or distance < nearest:
            nearest = distance
    if nearest is None:
        return None
    return int(round(nearest / _COVERAGE_ROUNDING_M) * _COVERAGE_ROUNDING_M)


def _occurrence_index(
    network: Network, statuses: frozenset[str],
) -> OccurrenceIndex:
    index: OccurrenceIndex = {}
    for pattern in network.patterns:
        if pattern.status not in statuses:
            continue
        for occurrence in pattern.stops:
            index.setdefault(occurrence.stop_id, []).append((pattern, occurrence))
    return index


def build_search_context(
    network: Network, req: PlanRequest, *, radius_m: float,
    statuses: frozenset[str], passenger_category: str, on: date,
) -> SearchContext:
    origin_stops = _eligible_stops(
        network, req.origin, radius_m=radius_m, boarding=True,
        allowed_statuses=statuses,
    )
    destination_stops = _eligible_stops(
        network, req.destination, radius_m=radius_m, boarding=False,
        allowed_statuses=statuses,
    )
    straight = {candidate.stop_id: candidate.straight_line_m for candidate in origin_stops}
    # Preserve the existing destination-distance precedence for overlapping stops.
    straight.update({
        candidate.stop_id: candidate.straight_line_m
        for candidate in destination_stops
    })
    index = _occurrence_index(network, statuses) if origin_stops and destination_stops else {}
    return SearchContext(
        network=network,
        origin_stops=origin_stops,
        destination_stops=destination_stops,
        destination_ids={candidate.stop_id for candidate in destination_stops},
        straight_line_by_stop=straight,
        occurrences_by_stop=index,
        allowed_statuses=statuses,
        passenger_category=passenger_category,
        on=on,
    )


def _best_alight(
    context: SearchContext, pattern: PatternData, board: PatternStopData,
) -> Optional[PatternStopData]:
    """Choose a later exit nearest the destination, keeping first-seen ties."""
    best = None
    for occurrence in pattern.stops:
        if (
            occurrence.sequence <= board.sequence
            or not occurrence.can_alight
            or occurrence.stop_id not in context.destination_ids
            or is_loop_ride(context.network, board, occurrence)
        ):
            continue
        key = (
            context.straight_line_by_stop.get(occurrence.stop_id, 0.0),
            occurrence.distance_along_m - board.distance_along_m,
        )
        if best is None or key < best[0]:
            best = (key, occurrence)
    return best[1] if best else None


def enumerate_direct(context: SearchContext) -> list[dict]:
    """Keep the first usable boarding occurrence for each direct pattern."""
    best: dict[str, RideLeg] = {}
    for origin in context.origin_stops:
        for pattern, board in context.occurrences_by_stop.get(origin.stop_id, ()):
            if not board.can_board or pattern.id in best:
                continue
            alight = _best_alight(context, pattern, board)
            if alight is not None:
                best[pattern.id] = RideLeg(pattern, board, alight)
    return [assemble_direct_option(context, leg) for leg in best.values()]


def _transfer_index(context: SearchContext) -> dict[str, list[TransferData]]:
    transfers_by_from: dict[str, list[TransferData]] = {}
    for connection in context.network.transfers:
        if connection.status in context.allowed_statuses:
            transfers_by_from.setdefault(connection.from_stop_id, []).append(connection)
    return transfers_by_from


def _last_destination_sequences(context: SearchContext) -> dict[str, int]:
    """Latest usable destination occurrence for each possible second pattern."""
    sequences: dict[str, int] = {}
    for destination in context.destination_stops:
        for pattern, occurrence in context.occurrences_by_stop.get(destination.stop_id, ()):
            if occurrence.can_alight:
                sequences[pattern.id] = max(
                    sequences.get(pattern.id, -1), occurrence.sequence,
                )
    return sequences


def _first_transfer_boardings(
    context: SearchContext, direct_patterns: frozenset[str],
) -> Iterator[tuple[PatternData, PatternStopData]]:
    seen_patterns = set()
    for origin in context.origin_stops:
        for pattern, board in context.occurrences_by_stop.get(origin.stop_id, ()):
            if (
                    not board.can_board
                    or pattern.id in direct_patterns
                    or pattern.id in seen_patterns
            ):
                continue
            # Only the nearest boarding occurrence is considered for a transfer.
            seen_patterns.add(pattern.id)
            yield pattern, board


def _transfer_stop_allowed(
    context: SearchContext, stop_id: str, *, boarding: bool,
) -> bool:
    """Exclude missing or disallowed transfer stops."""
    stop = context.network.stops.get(stop_id)
    if stop is None or stop.status not in context.allowed_statuses:
        return False
    return stop.can_board if boarding else stop.can_alight


def _transfer_candidates(
    context: SearchContext,
    first_boarding: tuple[PatternData, PatternStopData],
    transfers_by_from: dict[str, list[TransferData]],
    last_destination_sequences: dict[str, int],
    direct_patterns: frozenset[str],
) -> Iterator[TransferCandidate]:
    first_pattern, first_board = first_boarding
    for first_alight in first_pattern.stops:
        if first_alight.sequence <= first_board.sequence or not first_alight.can_alight:
            continue
        if is_loop_ride(context.network, first_board, first_alight):
            continue
        if not _transfer_stop_allowed(context, first_alight.stop_id, boarding=False):
            continue
        for connection in transfers_by_from.get(first_alight.stop_id, ()):
            if not _transfer_stop_allowed(context, connection.to_stop_id, boarding=True):
                continue
            for second_pattern, second_board in context.occurrences_by_stop.get(connection.to_stop_id, ()):
                if (
                    second_pattern.id == first_pattern.id
                    or not second_board.can_board
                    or second_pattern.id in direct_patterns
                    or last_destination_sequences.get(second_pattern.id, -1) <= second_board.sequence
                ):
                    continue
                second_alight = _best_alight(context, second_pattern, second_board)
                if second_alight is None:
                    continue
                ride_distance = (
                    first_alight.distance_along_m - first_board.distance_along_m
                    + second_alight.distance_along_m - second_board.distance_along_m
                )
                yield TransferCandidate(
                    first_leg=RideLeg(first_pattern, first_board, first_alight),
                    connection=connection,
                    second_leg=RideLeg(second_pattern, second_board, second_alight),
                    ride_distance_m=ride_distance,
                )


def enumerate_one_transfer(
    context: SearchContext, direct_patterns: frozenset[str] = frozenset(),
) -> list[dict]:
    """Keep the shortest ride per pattern pair through directed connections."""
    transfers_by_from = _transfer_index(context)
    last_destination_sequences = _last_destination_sequences(context)
    best: dict[tuple[str, str], TransferCandidate] = {}
    for first_boarding in _first_transfer_boardings(context, direct_patterns):
        candidates = _transfer_candidates(
            context, first_boarding, transfers_by_from,
            last_destination_sequences, direct_patterns,
        )
        for candidate in candidates:
            key = (candidate.first_leg.pattern.id, candidate.second_leg.pattern.id)
            # Equal distances retain the first candidate in network order.
            if key not in best or candidate.ride_distance_m < best[key].ride_distance_m:
                best[key] = candidate

    chosen = sorted(
        best.values(),
        key=lambda candidate: (
            candidate.ride_distance_m,
            candidate.first_leg.pattern.id,
            candidate.second_leg.pattern.id,
        ),
    )[:MAX_TRANSFER_CANDIDATES]
    return [assemble_transfer_option(context, candidate) for candidate in chosen]


def enumerate_options(context: SearchContext, max_transfers: int) -> list[dict]:
    options = enumerate_direct(context)
    if max_transfers >= 1:
        direct_patterns = frozenset(
            segment["route_pattern_id"]
            for option in options
            for segment in option["segments"]
            if segment["mode"] == "ride"
        )
        options += enumerate_one_transfer(context, direct_patterns)
    return options
