import base64
import json
from typing import Any
from litellm import acompletion
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def encode_image(image_path: str) -> str:
    """Return a base64-encoded string of the image at the given path."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

SYSTEM_PROMPT = """
You are an Expert UX/UI QA Engineer.

<task>
Identify all visual bugs in the provided web page screenshot and its corresponding simplified HTML DOM.
Visual bugs include: overlapping or clipped text, broken layout, misaligned elements, incorrect spacing, overflowing containers, contrast issues, hidden interactive elements, broken images, and layout shifts.
</task>

<process>
1. Examine the screenshot carefully for any visual anomalies
2. Cross-reference each anomaly with the DOM to identify the responsible element
3. For each bug found, pick the single best symptom keyword from the vocabulary below, then record the description, selector, and fix
</process>

<symptom_vocabulary>
Use EXACTLY one of these seven keywords as the symptom in every description. No synonyms, no free-form phrasing.
Keywords: hidden, clipped, overlapping, misaligned, collapsed, low-contrast, image-broken

hidden: element is not visible (off-screen, display none, opacity 0, or fully occluded)
clipped: element or its text is partially cut off, overflowing, or truncated
overlapping: element covers or is covered by another element unintentionally
misaligned: element has wrong position, spacing, or size relative to its container or siblings
collapsed: element layout broke (zero or near-zero height or width, wrapping failure)
low-contrast: text or UI element has insufficient color contrast against its background
image-broken: image fails to load or renders as a broken placeholder
</symptom_vocabulary>

<output_format>
You MUST respond with a single valid JSON object. No prose, no markdown, no code fences, no explanations before or after. Just the JSON object.

The object must have exactly one key "bugs" whose value is an array of bug objects.
Each bug object must have exactly these three fields:
"description": start with the element name (NEVER a leading "The", "A", or "An"), include exactly one symptom keyword from the vocabulary, no trailing punctuation, use identical wording regardless of which browser rendered the page. Format: "[Element] [symptom-keyword] on [location]" or "[Element] [symptom-keyword]". When the bug appears on small or narrow screens always write "on narrow viewports (mobile devices)". Examples: "Search bar clipped on narrow viewports (mobile devices)", "Logo misaligned in header"
"element_selector": the HTML tag, id, or class responsible (infer from the DOM)
"suggested_solution": a concrete technical fix (free-form)

If there are no bugs respond with: {"bugs": []}
</output_format>

<example>
{"bugs": [
  {
    "description": "Submit button clipped on narrow viewports (mobile devices)",
    "element_selector": "button#submit-btn",
    "suggested_solution": "Remove fixed width; use horizontal padding instead so the button scales with its label"
  },
  {
    "description": "Navigation bar overlapping hero image on scroll",
    "element_selector": ".navbar",
    "suggested_solution": "Add position: sticky and z-index: 100 to .navbar so it stays above page content"
  }
]}
</example>
"""


def _extract_bugs(content: str) -> list[dict[str, Any]] | None:
    """
    Try to parse bugs from a string that should contain JSON.
    Returns a list on success, None if the content cannot be parsed.
    """
    # Strip markdown fences
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    if not content:
        return []

    def _from_parsed(parsed: Any) -> list[dict[str, Any]] | None:
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("bugs", "visual_bugs", "issues", "errors", "results"):
                val = parsed.get(key)
                if isinstance(val, list):
                    return val
            # Single-key dict whose value is a list
            if len(parsed) == 1:
                val = next(iter(parsed.values()))
                if isinstance(val, list):
                    return val
        return None

    # Try parsing the whole content
    try:
        return _from_parsed(json.loads(content))
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object or array anywhere in the response
    for start_char in ('{', '['):
        idx = content.find(start_char)
        if idx != -1:
            try:
                result = _from_parsed(json.loads(content[idx:]))
                if result is not None:
                    return result
            except json.JSONDecodeError:
                pass

    return None


async def analyze_ui(image_path: str, dom_html: str, model_name: str, api_key: str) -> list[dict[str, Any]]:
    try:
        base64_image = encode_image(image_path)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": f"<dom_structure>\n{dom_html}\n</dom_structure>\n\nIdentify all visual bugs in the screenshot and DOM above."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ]

        logger.info(f"Sending request to {model_name}...")

        # Request JSON object mode; providers that don't support it fall back gracefully via LiteLLM.
        try:
            response = await acompletion(
                model=model_name,
                messages=messages,
                temperature=0.1,
                api_key=api_key,
                num_retries=0,
                timeout=60,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            if "response_format" in str(e).lower() or "json_object" in str(e).lower():
                logger.warning("Provider does not support response_format — retrying without it")
                response = await acompletion(
                    model=model_name,
                    messages=messages,
                    temperature=0.1,
                    api_key=api_key,
                    num_retries=0,
                    timeout=60,
                )
            else:
                raise

        content = (response.choices[0].message.content or "").strip()
        logger.info("AI Response received.")

        bugs = _extract_bugs(content)
        if bugs is None:
            logger.warning(f"Model returned non-JSON content: {content[:200]!r}")
            return []
        return bugs

    except Exception as e:
        error_msg = str(e)
        logger.error(f"AI Analysis failed: {error_msg}")

        if "RateLimitError" in error_msg or "429" in error_msg or "quota" in error_msg.lower():
            raise Exception("Rate limit or quota exceeded. Please check your API provider billing and limits.")
        elif "AuthenticationError" in error_msg or "401" in error_msg:
            raise Exception("Authentication failed. Please verify your API key is correct.")
        elif "ContextWindowExceededError" in error_msg or "too large" in error_msg.lower():
            raise Exception("The page content is too large for this model's context window.")

        raise Exception("AI API request failed. See backend logs for details.")
