"""Smoke tests for crawler._repair_selector."""
from crawler import _repair_selector


def test_strips_trailing_contains_pseudo():
    assert _repair_selector('.card:contains("Foo")') == ".card"


def test_strips_trailing_has_text_pseudo():
    assert _repair_selector(".item:has-text('x')") == ".item"


def test_preserves_valid_pseudo_before_invalid_suffix():
    assert _repair_selector('.list li:nth-child(2):contains("x")') == ".list li:nth-child(2)"


def test_valid_selector_returns_none():
    assert _repair_selector("#submit-btn") is None


def test_pseudo_without_parens_is_left_untouched_and_returns_none():
    # jQuery's bare `:visible` (no arguments) isn't matched by the repair regex,
    # so there's nothing to strip and no retry is warranted.
    assert _repair_selector("button:visible") is None


def test_selector_that_becomes_empty_returns_none():
    assert _repair_selector(':contains("test")') is None
