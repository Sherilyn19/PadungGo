"""Build the only facts the AI model may see about one planned trip.

Everything here is copied or formatted from a planner option; nothing is
looked up, calculated or guessed. Deliberately left out: coordinates, place
names typed by the visitor, walking distances to the first/last stop, geometry
and database IDs. The model gets what it needs to say "take 17D at X, get off
at Y" and nothing that could identify where the visitor is.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

HISTORIC = "historic_not_field_verified"
VERIFIED = "verified"

# Stop and route names come from imported data, so keep them short and plain
# before they are placed inside a prompt.
MAX_NAME_LENGTH = 80
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

WAIT_NOTE = "Waiting time is unknown: no verified frequency data."


@dataclass(frozen=True)
class TripFacts:
    """Prompt facts plus the exact values an answer is checked against."""

    prompt_facts: dict          # sent to the model, nothing else is
    route_codes: tuple          # in travel order, one entry per ride
    stop_names: tuple           # every stop the answer must name
    other_names: tuple          # route names: allowed, but not required
    scarce_codes: tuple
    historic: bool
    fare_text: str | None       # e.g. "₱13.00"; None means the fare is unknown
    fare_is_approximate: bool
    ride_minutes: tuple         # known minutes per ride (None when unknown)
    transfer_walk_metres: tuple
    notices: tuple              # server-written warnings shown beside the answer


def clean_name(value) -> str:
    text = _CONTROL_CHARS.sub(" ", str(value or ""))
    return " ".join(text.split())[:MAX_NAME_LENGTH]


def format_pesos(centavos: int) -> str:
    return f"₱{centavos // 100:,}.{centavos % 100:02d}"


def _ride_minutes(seconds) -> int | None:
    """Whole minutes, at least 1; unknown stays unknown."""
    if type(seconds) is not int or seconds < 0:
        return None
    return max(1, round(seconds / 60))


def _fare(option: dict) -> tuple[str | None, bool]:
    """The total is shown only when the planner calls it complete and supported."""
    fare = option.get("fare") or {}
    centavos = fare.get("total_centavos")
    known = (
        fare.get("total_is_complete") is True
        and fare.get("status") in ("exact", "approximate")
        and type(centavos) is int
        and centavos >= 0
    )
    if not known:
        return None, False
    return format_pesos(centavos), fare["status"] == "approximate"


def _ride_step(number: int, ride: dict) -> dict:
    return {
        "step": number,
        "action": "ride",
        "route_code": clean_name(ride["route_code"]),
        "route_name": clean_name(ride.get("route_name")),
        "board_at": clean_name(ride["board_stop_name"]),
        "get_off_at": clean_name(ride["alight_stop_name"]),
        "scarce_service": ride.get("service_availability") == "scarce",
        "ride_minutes": _ride_minutes(ride.get("duration_seconds")),
    }


def _steps(segments: list[dict]) -> list[dict]:
    """Walk, ride and transfer steps in travel order, named from the rides."""
    steps = []
    for index, segment in enumerate(segments):
        number = len(steps) + 1
        mode = segment["mode"]
        if mode == "ride":
            steps.append(_ride_step(number, segment))
        elif mode == "transfer_walk":
            before, after = segments[index - 1], segments[index + 1]
            steps.append({
                "step": number,
                "action": "transfer_walk",
                "from_stop": clean_name(before["alight_stop_name"]),
                "to_stop": clean_name(after["board_stop_name"]),
                "walk_metres": segment["distance_m"] if type(segment.get("distance_m")) is int else None,
            })
        elif index == 0:
            steps.append({"step": number, "action": "walk_to_first_stop",
                          "stop": clean_name(segments[1]["board_stop_name"])})
        else:
            steps.append({"step": number, "action": "walk_to_destination",
                          "from_stop": clean_name(segments[index - 1]["alight_stop_name"])})
    return steps


def _notices(option: dict, historic: bool, scarce_codes: tuple) -> tuple:
    """Warnings written by the planner or by us, never by the model."""
    notices = list(option.get("warnings") or [])
    if scarce_codes:
        notices.append(
            f"{', '.join(scarce_codes)} is flagged scarce: commuters report few trips."
        )
    notices.append(WAIT_NOTE)
    notices.append("Walking to and from stops is a straight-line estimate, not a verified path.")
    if historic and not any("not field-verified" in n.casefold() for n in notices):
        notices.append("This route data is historic and not field-verified.")
    return tuple(dict.fromkeys(notices))


def build_trip_facts(option: dict) -> TripFacts:
    """Turn one planner option into prompt facts and the values to check against."""
    segments = option["segments"]
    steps = _steps(segments)
    ride_steps = [s for s in steps if s["action"] == "ride"]
    transfer_steps = [s for s in steps if s["action"] == "transfer_walk"]

    historic = (option.get("evidence") or {}).get("verification_status") != VERIFIED
    fare_text, approximate = _fare(option)
    scarce_codes = tuple(dict.fromkeys(s["route_code"] for s in ride_steps if s["scarce_service"]))

    stop_names = []
    for step in steps:
        for key in ("stop", "board_at", "get_off_at", "from_stop", "to_stop"):
            if step.get(key):
                stop_names.append(step[key])

    prompt_facts = {
        "data_status": HISTORIC if historic else VERIFIED,
        "transfers": option["transfers"],
        "steps": steps,
        "fare": (
            {"known": True, "total": fare_text, "certainty": "approximate" if approximate else "exact"}
            if fare_text else {"known": False}
        ),
        "waiting_time": "unknown",
    }
    return TripFacts(
        prompt_facts=prompt_facts,
        route_codes=tuple(s["route_code"] for s in ride_steps),
        stop_names=tuple(dict.fromkeys(stop_names)),
        other_names=tuple(n for n in dict.fromkeys(s["route_name"] for s in ride_steps) if n),
        scarce_codes=scarce_codes,
        historic=historic,
        fare_text=fare_text,
        fare_is_approximate=approximate,
        ride_minutes=tuple(s["ride_minutes"] for s in ride_steps),
        transfer_walk_metres=tuple(s["walk_metres"] for s in transfer_steps if s["walk_metres"] is not None),
        notices=_notices(option, historic, scarce_codes),
    )
