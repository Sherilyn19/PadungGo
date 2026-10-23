"""Query normalisation and location-search API regressions."""
from __future__ import annotations

import pytest

from transit.search_text import build_search_text, normalise_query
from transit.models import Area, Location


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Osmeña Blvd.", ["osmena", "blvd"]),
        ("A. Gabuya", ["a", "gabuya"]),
        ("...", []),
        ("", []),
        ("CEBU   south", ["cebu", "south"]),
        ("Café, A&B/C-D'E(F)", ["cafe", "a", "b", "c", "d", "e"]),
        ("Gabuya gabuya GABUYA south", ["gabuya", "south"]),
        ("one two three four five six seven eight",
         ["one", "two", "three", "four", "five", "six"]),
        ("one one two three four five six seven",
         ["one", "two", "three", "four", "five", "six"]),
        ("Osmen\u0303a", ["osmena"]),
    ],
)
def test_normalise_query(query, expected):
    assert normalise_query(query) == expected


def test_search_text_combines_name_and_aliases():
    assert build_search_text("Fuente Osmeña", "FO, Rotonda\nCircle") == (
        "fuente osmena fo rotonda circle")


@pytest.fixture
def locations(db):
    names = (
        "Cebu South Road & A Gabuya Street",
        "Fuente Osmena",
        "Tagunol St. & A Gabuya Street",
    )
    return [
        Location.objects.create(
            name=name,
            kind="place",
            latitude=10.3,
            longitude=123.9,
        )
        for name in names
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query,expected",
    [
        ("gabuya south", ["Cebu South Road & A Gabuya Street"]),
        (
            "a. gabuya",
            [
                "Cebu South Road & A Gabuya Street",
                "Tagunol St. & A Gabuya Street",
            ],
        ),
        ("osmeña", ["Fuente Osmena"]),
        ("CEBU   south", ["Cebu South Road & A Gabuya Street"]),
        ("zzz", []),
        ("south zzz", []),
    ],
)
def test_locations_match_all_normalised_tokens(client, locations, query, expected):
    response = client.get("/api/v1/locations", {"q": query})

    assert response.status_code == 200
    assert [row["name"] for row in response.json()["results"]] == expected


@pytest.mark.django_db
def test_punctuation_only_query_matches_empty_query(client, locations):
    empty = client.get("/api/v1/locations")
    punctuation = client.get("/api/v1/locations", {"q": "..."})

    assert empty.status_code == punctuation.status_code == 200
    assert punctuation.json() == empty.json()


@pytest.mark.django_db
def test_normalised_search_preserves_area_filter(client, locations):
    area = Area.objects.create(name="Search test area", kind="barangay")
    locations[2].area = area
    locations[2].save()

    response = client.get(
        "/api/v1/locations",
        {"q": "a. gabuya", "area_id": str(area.id)},
    )

    assert response.status_code == 200
    assert [row["name"] for row in response.json()["results"]] == [
        "Tagunol St. & A Gabuya Street"
    ]


@pytest.mark.django_db
def test_normalised_search_preserves_cursor_pagination(client, locations):
    first = client.get(
        "/api/v1/locations", {"q": "a. gabuya", "limit": 1}
    )
    assert first.status_code == 200
    first_page = first.json()
    assert [row["name"] for row in first_page["results"]] == [
        "Cebu South Road & A Gabuya Street"
    ]
    assert first_page["next_cursor"] is not None

    second = client.get(
        "/api/v1/locations",
        {
            "q": "a. gabuya",
            "limit": 1,
            "cursor": first_page["next_cursor"],
        },
    )
    assert second.status_code == 200
    second_page = second.json()
    assert [row["name"] for row in second_page["results"]] == [
        "Tagunol St. & A Gabuya Street"
    ]
    assert second_page["next_cursor"] is None