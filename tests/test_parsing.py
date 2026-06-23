"""Unit tests for the pure parsing helpers in download_brand_logos.py.

These cover the two functions that do the only non-trivial string logic in the
tool — turning a brands-file/CLI line into a (display_name, hint) pair, and
slugifying a display name into the folder/file stem used for output.
"""
import pytest

from download_brand_logos import parse_brand_entry, slugify


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Procter & Gamble", "procter-gamble"),  # README's canonical example
        ("Coca-Cola", "coca-cola"),
        ("  AT&T  ", "at-t"),                     # surrounding whitespace stripped
        ("Realty Income Corporation", "realty-income-corporation"),
        ("apple", "apple"),
        ("Hello!!!", "hello"),                    # trailing punctuation collapses + strips
        ("--Nike--", "nike"),                     # leading/trailing separators stripped
        ("", "brand"),                            # empty -> fallback slug
        ("###", "brand"),                         # nothing alphanumeric -> fallback slug
    ],
)
def test_slugify(raw, expected):
    assert slugify(raw) == expected


@pytest.mark.parametrize(
    "line, expected",
    [
        # bare domain -> display name derived from the first label, hint is the domain
        ("apple.com", ("apple", "apple.com")),
        ("nike.com", ("nike", "nike.com")),
        # domain with a path -> name is still the first label; hint keeps the whole token
        ("apple.com/brand", ("apple", "apple.com/brand")),
        # "Name = domain" -> explicit display name + exact domain, both trimmed
        ("Procter & Gamble = pg.com", ("Procter & Gamble", "pg.com")),
        ("Coca-Cola = coca-cola.com", ("Coca-Cola", "coca-cola.com")),
        ("  GitHub   =   github.com  ", ("GitHub", "github.com")),
        # bare name (no '=' and no '.') -> resolved via Search API later; name == hint
        ("Starbucks", ("Starbucks", "Starbucks")),
    ],
)
def test_parse_brand_entry(line, expected):
    assert parse_brand_entry(line) == expected


def test_equals_takes_precedence_over_dot():
    # A line containing both '=' and '.' is a Name=domain pair, not a bare domain.
    assert parse_brand_entry("Berkshire = brk.com") == ("Berkshire", "brk.com")


def test_slug_is_shared_by_folder_and_file_stem():
    # slugify drives both logos/<slug>/ and <slug>_<type>_<theme>.<ext>, so the
    # folder name and file prefix must agree for the README's example.
    name = "Procter & Gamble"
    assert slugify(name) == "procter-gamble"
