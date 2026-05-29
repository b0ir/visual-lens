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
3. For each bug found, record a concise description, the responsible element selector, and a concrete fix
</process>

<output_format>
IMPORTANT: Your response must start with [ and end with ]. Output the JSON array and nothing else.
No explanations, no markdown, no code fences, no introductory text. Just the raw JSON array.

Each object must have exactly these three fields:
- "description": concise, browser-agnostic description. STRICT rules: (1) start directly with the element name — NEVER a leading article such as "The", "A", or "An"; (2) no trailing punctuation; (3) use IDENTICAL wording regardless of which browser rendered the page — the same underlying bug must produce the exact same description string across all browsers. Use the pattern "[Element] [symptom]", e.g., "Search bar hidden on narrow viewports (mobile devices)", "Logo not centered in header". When a bug manifests on narrow/small screens, always use the phrasing "narrow viewports (mobile devices)"
- "element_selector": the HTML tag, id, or class responsible (infer from the DOM)
- "suggested_solution": a concrete technical fix

If there are absolutely no bugs, return an empty array: []
</output_format>

<example>
[
  {
    "description": "Submit button text clipped — label overflows button boundary on narrow viewports (mobile devices)",
    "element_selector": "button#submit-btn",
    "suggested_solution": "Remove fixed width; use horizontal padding instead so the button scales with its label"
  },
  {
    "description": "Navigation bar overlaps hero image content on scroll due to missing stacking context",
    "element_selector": ".navbar",
    "suggested_solution": "Add position: sticky and z-index: 100 to .navbar so it stays above page content"
  }
]
</example>
"""

async def analyze_ui(image_path: str, dom_html: str, model_name: str, api_key: str) -> list[dict[str, Any]]:
    """
    Analyze a UI screenshot using a vision-capable LLM.

    Args:
        image_path: Path to the screenshot file.
        dom_html: Simplified HTML DOM string.
        model_name: LiteLLM model identifier (e.g., "openai/gpt-4.1").
        api_key: The provider's API key, passed directly to LiteLLM.
    """
    try:
        base64_image = encode_image(image_path)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": f"<dom_structure>\n{dom_html}\n</dom_structure>\n\nIdentify all visual bugs in the screenshot and DOM above."} ,
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ]

        logger.info(f"Sending request to {model_name}...")
        response = await acompletion(
            model=model_name,
            messages=messages,
            temperature=0.1,
            api_key=api_key,
            num_retries=0,
            timeout=60,
        )

        content = (response.choices[0].message.content or "").strip()
        logger.info(f"AI Response received.")

        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
        content = content.strip()
        if not content:
            return []
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Some models prepend prose before the JSON array — try to find and extract it
            start = content.find('[')
            if start != -1:
                try:
                    return json.loads(content[start:])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Model returned non-JSON content: {content[:200]!r}")
            return []
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
