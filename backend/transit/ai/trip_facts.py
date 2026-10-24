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

# Imported feeds sometimes have no stop name and the importer writes a
# placeholder such as "Unnamed stop (feed id 2939)". Like the app screen, the
# model is told only that the stop has no known name, and its answer is not
# required to repeat the placeholder.
UNNAMED_STOP = "the stop shown on the map"
_UNNAMED_PREFIX = re.compile(r"^unnamed stop", re.I)


@dataclass(frozen=True)
class TripFacts:
    """Prompt facts plus the exact values an answer is checked against."""

    prompt_facts: dict          # sent to the model, nothing else is
    route_codes: tuple          # in travel order, one entry per ride
    stop_names: tuple           # stops the answer must name: where to get off or transfer
    other_names: tuple          # boarding stops and route names: allowed, not required
    scarce_codes: tuple
    transfers: int
    historic: bool
    notices: tuple              # server-written warnings shown beside the answer


def clean_name(value) -> str:
    text = _CONTROL_CHARS.sub(" ", str(value or ""))
    return " ".join(text.split())[:MAX_NAME_LENGTH]


def stop_label(value) -> str:
    """A stop name that is safe to put in a prompt; placeholders become UNNAMED_STOP."""
    name = clean_name(value)
    return UNNAMED_STOP if _UNNAMED_PREFIX.match(name) else name


def _ride_step(number: int, ride: dict) -> dict:
    return {
        "step": number,
        "action": "ride",
        "route_code": clean_name(ride["route_code"]),
        "route_name": clean_name(ride.get("route_name")),  # allowed in an answer, never sent
        "board_at": stop_label(ride["board_stop_name"]),
        "get_off_at": stop_label(ride["alight_stop_name"]),
        "scarce_service": ride.get("service_availability") == "scarce",
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
                "from_stop": stop_label(before["alight_stop_name"]),
                "to_stop": stop_label(after["board_stop_name"]),
                # The planner links a stop to itself when both rides use the same stop.
                "same_stop": segment.get("from_stop_id") is not None
                             and segment.get("from_stop_id") == segment.get("to_stop_id"),
            })
        elif index == 0:
            steps.append({"step": number, "action": "walk_to_first_stop",
                          "stop": stop_label(segments[1]["board_stop_name"])})
        else:
            steps.append({"step": number, "action": "walk_to_destination",
                          "from_stop": stop_label(segments[index - 1]["alight_stop_name"])})
    return steps


def _model_view(steps: list[dict]) -> list[dict]:
    """What the model sees of each step. The screen already shows fares, minutes,
    distances and route names, so none of them are sent: the model cannot repeat,
    or get wrong, what it was never given."""
    keep = {
        "ride": ("step", "action", "route_code", "board_at", "get_off_at", "scarce_service"),
        "transfer_walk": ("step", "action", "from_stop", "to_stop", "same_stop"),
    }
    return [
        {key: step[key] for key in keep.get(step["action"], tuple(step)) if key in step}
        for step in steps
    ]


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

    historic = (option.get("evidence") or {}).get("verification_status") != VERIFIED
    scarce_codes = tuple(dict.fromkeys(s["route_code"] for s in ride_steps if s["scarce_service"]))

    def names(keys):
        found = (step.get(key) for step in steps for key in keys)
        return tuple(dict.fromkeys(n for n in found if n and n != UNNAMED_STOP))

    # The answer must say where to hop off and where to change. Boarding stops are
    # optional (they are often unnamed, and the steps below the summary list them).
    required_stops = names(("get_off_at", "from_stop", "to_stop"))
    prompt_facts = {"transfers": option["transfers"], "steps": _model_view(steps)}
    return TripFacts(
        prompt_facts=prompt_facts,
        route_codes=tuple(s["route_code"] for s in ride_steps),
        stop_names=required_stops,
        other_names=tuple(dict.fromkeys(
            [*names(("stop", "board_at")), *(s["route_name"] for s in ride_steps if s["route_name"])]
        )),
        scarce_codes=scarce_codes,
        transfers=option["transfers"],
        historic=historic,
        notices=_notices(option, historic, scarce_codes),
    )
