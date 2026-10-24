"""Accept an AI answer only if it keeps the planner's facts and adds none.

A model can still make a mistake that no rule here would catch, so these checks
are a safety net, not proof that every sentence is true. They catch the
failures that matter most for a commuter:

* a missing or reordered route code, or a missing stop name;
* a route code, price, time or distance that is not in the planner's data;
* a certainty the planner does not have (frequency, "running now", official);
* a missing warning (historic data, scarce route, unknown fare or waiting time).

`check_explanation` returns None when the answer is acceptable, or a short
reason code. The reason is for logs and tests; it is never shown to visitors.
"""
from __future__ import annotations

import re
from decimal import Decimal

from .trip_facts import TripFacts

MAX_CHARS = 900

_FLAGS = re.I
_UNKNOWN_WORDS = (
    r"unknown|unclear|uncertain|unconfirmed"
    r"|not (?:confirmed|known|available|certain|guaranteed|verified)"
    r"|(?:isn|aren|can|couldn)['’]?t (?:be )?(?:known|confirmed|available|certain|say|tell|predict)"
    r"|cannot (?:say|tell|predict|be sure)"
    r"|no (?:verified |reliable |confirmed )?(?:frequency|timetable|schedule|fare|information|info|data)"
    r"|(?:could|can)(?:n['’]t| not) (?:be )?(?:determined|calculated|confirmed|found|known)|not sure"
    r"|unavailable|(?:don|doesn)['’]t (?:have|know)"
    r"|not (?:provided|listed|set|shown|given|specified|included)"
    r"|ask (?:the|your) (?:driver|conductor)"
)
_HEDGE_WORDS = r"confirm|check|make sure|whether|ask|may|might|could|not sure|unknown|not field"

_MONEY = re.compile(
    r"(?:₱|\bphp\s?|\bp(?=\d))\s*(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*(?:pesos?|php)\b", _FLAGS)
_DURATION = re.compile(
    r"(\d+(?:\.\d+)?)(?:\s*(?:-|–|to)\s*\d+(?:\.\d+)?)?[\s-]*(minutes?|mins?|hours?|hrs?)\b", _FLAGS)
_DISTANCE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(km|kilomet(?:er|re)s?|met(?:er|re)s?|m)\b", _FLAGS)
_UNIT = r"minutes?|mins?|hours?|hrs?|pesos?|kilomet(?:er|re)s?|met(?:er|re)s?"
_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_WORD = "|".join(_NUMBER_WORDS)
# "eight minutes", "twenty-one minutes", "one hundred pesos"
_SPELLED_QUANTITY = re.compile(
    rf"\b((?:(?:{_WORD}|hundred)(?:[\s-]+|\b))+)\s*({_UNIT})\b", _FLAGS)
# "an hour", "a minute"
_ONE_UNIT = re.compile(r"\ban?\s+(hour|minute)\b", _FLAGS)
_VAGUE_TIME = re.compile(r"\b(?:half an? hour|quarter of an hour|couple of (?:minutes|hours))\b", _FLAGS)
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.M)
_ROUTE_CODE_LIKE = re.compile(r"(?<![A-Za-z0-9])\d{1,2}[A-Z]{1,2}(?![A-Za-z0-9])")
# "not field-verified", "has not yet been verified", "no verified schedule", "unverified"
_NOT_VERIFIED = re.compile(
    r"\b(?:not|never|non|no|without|isn['’]t|hasn['’]t|haven['’]t)\b[\w\s'’-]{0,14}?\bverified\b|\bunverified\b", _FLAGS)
_NEGATED_GUARANTEE = re.compile(r"\b(?:no|not|never|without|n['’]t)\s+(?:\w+\s+)?guarantee[sd]?\b", _FLAGS)

# Each pattern is a claim the planner cannot support.
_UNSUPPORTED_CLAIMS = (
    (re.compile(r"\bfrequent(?:ly)?\b|\bevery\s+(?:\d+|few|couple|other|hour|minute)\b"
                r"|\bregular(?:ly)?\s+(?:service|trips|intervals|schedule)\b", _FLAGS), "frequency_claim"),
    # scarce_service false only means no report exists; it never means "not scarce" or common.
    # "not flagged as scarce" describes the data and is allowed.
    (re.compile(r"\b(?:not|isn['’]t|never|no)\b(?!\s+flagged)\s+(?:\w+\s+){0,2}scarc\w*"
                r"|\b(?:plenty of|lots of|readily available|easy to (?:find|catch))\b", _FLAGS), "scarcity_claim"),
    (re.compile(r"\b24\s*/\s*7\b|\b24\s+hours\b|\ball day\b|\b(?:around|round) the clock\b", _FLAGS),
     "operating_hours_claim"),
    (re.compile(r"\bguarantee[sd]?\b", _FLAGS), "certainty_claim"),
    (re.compile(r"\b(?:cheapest|fastest|quickest|shortest|best|recommended|easiest)\b", _FLAGS), "ranking_claim"),
    (re.compile(r"\balternativ\w*|\banother route\b|\bother routes?\b", _FLAGS), "extra_route"),
    # Checked after real stop and route names are removed, so only invented places remain.
    (re.compile(r"\b(?:street|avenue|boulevard|highway|terminal|mall|church|hospital|school|bridge"
                r"|junction|market|landmark|corner of)\b", _FLAGS), "invented_landmark"),
)
_CURRENT_OPERATION = re.compile(
    r"\b(?:currently|still|now|today|right now)\b[^.!?\n]{0,25}\b(?:running|operating|operates|runs|available|in service)\b"
    r"|\b(?:is|are)\s+(?:running|operating)\b", _FLAGS)


# Models often write look-alike characters: a non-breaking hyphen in "field‑verified",
# or a narrow no-break space in "13 minutes". Map them to plain ones so the checks see
# the same words a reader does.
_LOOK_ALIKES = str.maketrans({
    **{ord(c): "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"},
    **{ord(c): " " for c in "\u00a0\u2007\u2009\u200a\u202f\u2002\u2003"},
    ord("\u200b"): None, ord("\u2060"): None, ord("\ufeff"): None,   # zero-width characters
    ord("\u2019"): "'", ord("\u2018"): "'",
})


def clean_explanation(raw: str) -> str:
    """Tidy harmless formatting (bold markers, look-alike characters, stray spaces) before checking."""
    text = raw.translate(_LOOK_ALIKES).replace("**", "").replace("__", "")
    lines = [" ".join(line.split()) for line in text.strip().splitlines()]
    return "\n".join(line for line in lines if line)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold().replace("&", " and "))


def _name_pattern(name: str) -> re.Pattern | None:
    """Match a name even if the model writes '&' as 'and' or drops punctuation."""
    tokens = _words(name)
    if not tokens:
        return None
    body = r"\W+".join(r"(?:and|&)" if token == "and" else re.escape(token) for token in tokens)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", _FLAGS)


def _code_pattern(code: str) -> re.Pattern:
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(code)}(?![A-Za-z0-9])", _FLAGS)


def _sentences(text: str) -> list[str]:
    return [part for part in re.split(r"[.!?\n]+", text) if part.strip()]


def _sentence_has(text: str, topic: str, wording: str) -> bool:
    """True if one sentence contains both the topic word and the wording."""
    return any(re.search(topic, s, _FLAGS) and re.search(wording, s, _FLAGS) for s in _sentences(text))


def _shape_problem(text: str) -> str | None:
    if not text:
        return "empty"
    if len(text) > MAX_CHARS:
        return "too_long"
    if re.search(r"</?[a-z!]|```|\]\(|https?://|www\.", text, _FLAGS):
        return "markup_or_link"
    return None


def _route_problem(text: str, facts: TripFacts) -> str | None:
    first_seen = []
    for code in dict.fromkeys(facts.route_codes):
        match = _code_pattern(code).search(text)
        if match is None:
            return "missing_route_code"
        first_seen.append(match.start())
    if first_seen != sorted(first_seen):
        return "wrong_route_order"
    return None


def _missing_stop_name(text: str, facts: TripFacts) -> bool:
    patterns = (_name_pattern(name) for name in facts.stop_names)
    return any(pattern and not pattern.search(text) for pattern in patterns)


def _without_known_names(text: str, facts: TripFacts) -> str:
    """The text with real route codes, stop names and route names blanked out."""
    for code in facts.route_codes:
        text = _code_pattern(code).sub(" ", text)
    for name in (*facts.stop_names, *facts.other_names):
        pattern = _name_pattern(name)
        if pattern:
            text = pattern.sub(" ", text)
    return text


def _number_from_words(words: str) -> int:
    total = 0
    for word in re.split(r"[\s-]+", words.casefold().strip()):
        if word == "hundred":
            total = max(total, 1) * 100
        elif word in _NUMBER_WORDS:
            total += _NUMBER_WORDS[word]
    return total


def _with_digits(text: str) -> str:
    """Spell out quantities as digits so they are checked like any other number."""
    text = _SPELLED_QUANTITY.sub(lambda m: f" {_number_from_words(m.group(1))} {m.group(2)} ", text)
    return _ONE_UNIT.sub(lambda m: f" 1 {m.group(1)} ", text)


def _decimal(text: str) -> Decimal:
    return Decimal(text.replace(",", ""))


def _number_problem(rest: str, facts: TripFacts) -> str | None:
    """Every route code, price, time, distance and number must come from the planner."""
    # Real codes are already blanked out, so any code-shaped token left is invented.
    if _ROUTE_CODE_LIKE.search(rest):
        return "unknown_route_code"
    if _VAGUE_TIME.search(rest):
        return "invented_time"
    rest = _with_digits(rest)
    allowed_price = _decimal(facts.fare_text[1:]) if facts.fare_text else None
    for match in _MONEY.finditer(rest):
        if allowed_price is None:
            return "invented_fare"
        if _decimal(match.group(1) or match.group(2)) != allowed_price:
            return "wrong_fare"
    rest = _MONEY.sub(" ", rest)

    known_minutes = {m for m in facts.ride_minutes if m is not None}
    if facts.ride_minutes and None not in facts.ride_minutes:
        known_minutes.add(sum(facts.ride_minutes))
    for match in _DURATION.finditer(rest):
        value = _decimal(match.group(1)) * (60 if match.group(2).casefold().startswith(("h")) else 1)
        if value not in known_minutes:
            return "invented_time"
    rest = _DURATION.sub(" ", rest)

    known_metres = set(facts.transfer_walk_metres)
    for match in _DISTANCE.finditer(rest):
        value = _decimal(match.group(1)) * (1000 if match.group(2).casefold().startswith("k") else 1)
        if value not in known_metres:
            return "invented_distance"
    rest = _DISTANCE.sub(" ", rest)

    # Only the number of rides or transfers (or a list marker) may remain as a digit.
    allowed = {str(len(facts.route_codes)), str(facts.transfers)}
    leftover = re.findall(r"\d+", _LIST_MARKER.sub(" ", rest))
    if any(number not in allowed for number in leftover):
        return "invented_number"
    return None


def _claim_problem(text: str, rest: str, facts: TripFacts) -> str | None:
    for pattern, reason in _UNSUPPORTED_CLAIMS:
        # Landmark words are only suspicious outside the real stop names.
        haystack = rest if reason == "invented_landmark" else text
        if reason == "certainty_claim":
            haystack = _NEGATED_GUARANTEE.sub(" ", haystack)
        if pattern.search(haystack):
            return reason
    for sentence in _sentences(text):
        if _CURRENT_OPERATION.search(sentence) and not re.search(_HEDGE_WORDS, sentence, _FLAGS):
            return "current_operation_claim"
    if facts.historic and re.search(r"\bverified\b", _NOT_VERIFIED.sub(" ", text), _FLAGS):
        return "verification_claim"
    return None


def _missing_warning(text: str, facts: TripFacts) -> str | None:
    """Warnings the planner requires must survive the rewrite."""
    if facts.historic and not _NOT_VERIFIED.search(text):
        return "missing_historic_warning"
    if facts.scarce_codes and not re.search(r"\bscarce\b", text, _FLAGS):
        return "missing_scarce_warning"
    if facts.fare_text is None and not _sentence_has(text, r"\bfare", _UNKNOWN_WORDS):
        return "missing_unknown_fare"
    if facts.fare_text and facts.fare_is_approximate and not re.search(
        r"\bapproximate|\babout\b|\baround\b|\bestimate", text, _FLAGS
    ):
        return "missing_approximate_fare"
    if not _sentence_has(text, r"\bwait", _UNKNOWN_WORDS):
        return "missing_unknown_wait"
    return None


def check_explanation(text: str, facts: TripFacts) -> str | None:
    """None if `text` is acceptable for this trip, otherwise a reason code."""
    problem = _shape_problem(text) or _route_problem(text, facts)
    if problem:
        return problem
    if _missing_stop_name(text, facts):
        return "missing_stop_name"
    rest = _without_known_names(text, facts)
    return _number_problem(rest, facts) or _claim_problem(text, rest, facts) or _missing_warning(text, facts)
