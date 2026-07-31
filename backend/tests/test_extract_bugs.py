"""Smoke tests for ai_provider._extract_bugs JSON parsing."""
from ai_provider import _extract_bugs


def test_plain_json_array():
    assert _extract_bugs('[{"symptom": "clipped"}]') == [{"symptom": "clipped"}]


def test_markdown_fenced_json():
    content = '```json\n[{"symptom": "hidden"}]\n```'
    assert _extract_bugs(content) == [{"symptom": "hidden"}]


def test_bare_fence_without_lang():
    content = '```\n[{"symptom": "overlapping"}]\n```'
    assert _extract_bugs(content) == [{"symptom": "overlapping"}]


def test_known_key_wrapped_object():
    assert _extract_bugs('{"bugs": [{"symptom": "misaligned"}]}') == [
        {"symptom": "misaligned"}
    ]


def test_single_key_object_with_list_value():
    assert _extract_bugs('{"anything": [{"symptom": "collapsed"}]}') == [
        {"symptom": "collapsed"}
    ]


def test_json_embedded_after_prose():
    content = 'Here are the issues I found:\n[{"symptom": "low-contrast"}]'
    assert _extract_bugs(content) == [{"symptom": "low-contrast"}]


def test_empty_content_returns_empty_list():
    assert _extract_bugs("") == []


def test_non_json_returns_none():
    assert _extract_bugs("No bugs were found on this page.") is None


def test_reasoning_model_prose_before_and_after_json():
    content = """The user wants me to identify visual bugs in the provided screenshot and DOM.

1. Analyze the Screenshot:
- Top Banner: There's a dark grey banner at the top.

```json
{"bugs": [{"description": "Search input has no label", "category": "misaligned", "element_selector": "#search"}]}
```

Hope this summary helps!"""
    assert _extract_bugs(content) == [
        {"description": "Search input has no label", "category": "misaligned", "element_selector": "#search"}
    ]

