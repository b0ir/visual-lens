import base64
import json
from typing import Any
import litellm
from litellm import acompletion
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.WARNING)


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
1. Examine the screenshot for clearly visible anomalies. If you cannot see the problem in the screenshot, do not report it — DOM analysis alone is not sufficient.
2. Cross-reference each confirmed visual anomaly with the DOM to identify the responsible element.
3. For each bug found, write a free-form description of the symptom, classify it into the category list below, and record the description, category, selector, and fix.
Note: minor typographic and sub-pixel rendering differences between browsers (e.g., font hinting, 1-2px position variance) are NOT bugs. Only report cross-browser differences that visibly impact layout or usability.
</process>

<category_vocabulary>
Classify every bug into exactly one of these eight categories (use "other" only when none of the first seven genuinely fit):
hidden, clipped, overlapping, misaligned, collapsed, low-contrast, image-broken, other

hidden: element is not visible to a user in the screenshot (off-screen, display none, opacity 0, or fully occluded by another element)
clipped: element or its text is partially cut off, overflowing, or truncated — visible in the screenshot
overlapping: element clearly covers or is covered by another element unintentionally — both elements must be visible
misaligned: element has clearly visible and significant wrong position, spacing, or size relative to its container or siblings; not minor pixel-level variance
collapsed: element layout visibly broke (zero or near-zero height or width, wrapping failure) — must be visible in the screenshot
low-contrast: text or UI element has quantifiably poor contrast — the text is genuinely hard to read against its background in the screenshot
image-broken: the browser's broken-image icon or gray placeholder must be visibly present in the screenshot — do NOT report based on DOM inference alone
other: a clearly visible visual bug that does not fit any category above
</category_vocabulary>

<output_format>
You MUST respond with a single valid JSON object. No prose, no markdown, no code fences, no explanations before or after. Just the JSON object.

The object must have exactly one key "bugs" whose value is an array of bug objects.
Each bug object must have exactly these five fields:
"description": start with the element name (NEVER a leading "The", "A", or "An"), no trailing punctuation, use identical wording regardless of which browser rendered the page — describe the symptom freely in your own words. Format: "[Element] [symptom] on [location]" or "[Element] [symptom]". When the bug appears on small or narrow screens always write "on narrow viewports (mobile devices)". Examples: "Search bar overflows its container on narrow viewports (mobile devices)", "Logo sits noticeably off-center in header"
"category": exactly one of: hidden, clipped, overlapping, misaligned, collapsed, low-contrast, image-broken, other — see <category_vocabulary> above
"element_selector": a single syntactically valid CSS selector (standard CSS, parseable by document.querySelector — NOT jQuery-style pseudo-classes like :contains(), :visible, or :has-text()) that uniquely identifies the responsible element. Prefer, in order: (1) an id selector (#some-id), (2) a stable data-* attribute ([data-testid="..."]), (3) a specific class selector, (4) a tag+nth-of-type chain (e.g. "ul.nav > li:nth-of-type(3)") scoped narrowly enough to resolve to exactly one element. Do not use a bare tag name (div, span, p) alone.
"suggested_solution": a concrete technical fix (free-form)
"confidence": integer 1-5, where 5 = certain (clearly visible in screenshot), 3 = probable, 1 = speculative. Only report bugs you would rate 3 or above.

If there are no bugs respond with: {"bugs": []}
Important: only report bugs you can clearly see in the screenshot. Visual confirmation is required — do not infer bugs from DOM alone. When in doubt, do not report. A false positive is worse than a missed bug.
</output_format>

<example>
{"bugs": [
  {
    "description": "Submit button overflows its container on narrow viewports (mobile devices)",
    "category": "clipped",
    "element_selector": "button#submit-btn",
    "suggested_solution": "Remove fixed width; use horizontal padding instead so the button scales with its label",
    "confidence": 5
  },
  {
    "description": "Navigation bar sits on top of the hero image when the page is scrolled",
    "category": "overlapping",
    "element_selector": ".navbar",
    "suggested_solution": "Add position: sticky and z-index: 100 to .navbar so it stays above page content",
    "confidence": 4
  }
]}
</example>
"""

VALID_CATEGORIES = {"hidden", "clipped", "overlapping", "misaligned", "collapsed", "low-contrast", "image-broken", "other"}


def _normalize_category(category: Any) -> str:
    """Return category lowercased if it's one of the known values, else "other"."""
    if isinstance(category, str) and category.strip().lower() in VALID_CATEGORIES:
        return category.strip().lower()
    return "other"


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
                max_tokens=4096,
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
                    max_tokens=4096,
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
        # Drop low-confidence detections, strip the internal confidence field,
        # and normalize category to a known value (defaulting to "other").
        filtered = []
        for b in bugs:
            try:
                if int(b.get("confidence", 3)) < 3:
                    continue
            except (TypeError, ValueError):
                continue
            b.pop("confidence", None)
            b["category"] = _normalize_category(b.get("category"))
            filtered.append(b)
        return filtered

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
