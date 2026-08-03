"""Smoke tests for ai_provider._normalize_category."""
from ai_provider import _normalize_category


def test_known_category_passes_through():
    assert _normalize_category("clipped") == "clipped"


def test_known_category_is_case_and_whitespace_normalized():
    assert _normalize_category("  Overlapping  ") == "overlapping"


def test_unknown_category_defaults_to_other():
    assert _normalize_category("z-index-war") == "other"


def test_missing_category_defaults_to_other():
    assert _normalize_category(None) == "other"


def test_non_string_category_defaults_to_other():
    assert _normalize_category(5) == "other"


def test_other_is_itself_valid():
    assert _normalize_category("other") == "other"
