"""Tests for GitHub Link header pagination helpers."""

from __future__ import annotations

from app.collector.github.client import build_pagination_info, parse_link_header


def test_parse_link_header_extracts_relations() -> None:
    """Link headers should be parsed into rel-to-URL mappings."""
    link_header = (
        '<https://api.github.com/repos/octo/repo/pulls?page=2>; rel="next", '
        '<https://api.github.com/repos/octo/repo/pulls?page=5>; rel="last", '
        '<https://api.github.com/repos/octo/repo/pulls?page=1>; rel="first", '
        '<https://api.github.com/repos/octo/repo/pulls?page=1>; rel="prev"'
    )

    links = parse_link_header(link_header)

    assert links["next"].endswith("page=2")
    assert links["last"].endswith("page=5")
    assert links["first"].endswith("page=1")
    assert links["prev"].endswith("page=1")


def test_parse_link_header_returns_empty_mapping_for_missing_header() -> None:
    """Missing Link headers should produce an empty mapping."""
    assert parse_link_header(None) == {}
    assert parse_link_header("") == {}


def test_build_pagination_info_exposes_page_navigation() -> None:
    """Pagination metadata should expose page numbers and navigation flags."""
    headers = {
        "link": (
            '<https://api.github.com/repos/octo/repo/pulls?page=3>; rel="next", '
            '<https://api.github.com/repos/octo/repo/pulls?page=10>; rel="last", '
            '<https://api.github.com/repos/octo/repo/pulls?page=1>; rel="prev"'
        ),
    }

    pagination = build_pagination_info(headers, current_page=2)

    assert pagination.current_page == 2
    assert pagination.next_page == 3
    assert pagination.previous_page == 1
    assert pagination.last_page == 10
    assert pagination.has_next is True
    assert pagination.has_previous is True
