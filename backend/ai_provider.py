import os
import base64
import json
from litellm import acompletion
import logging

logging.basicConfig(level=logging.INFO)

def encode_image(image_path: str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

SYSTEM_PROMPT = """
You are an Expert UX/UI QA Engineer. Analyze the provided web page screenshot and its corresponding simplified HTML DOM.
Your goal is to find visual bugs, such as overlapping text, broken elements, contrast issues, or layout shifts.

You MUST return ONLY a valid JSON array of objects. Do not include markdown formatting like ```json.
Format exactly like this:
[
  {
    "description": "Short description of the bug (e.g., 'Submit button text overlaps the border')",
    "element_selector": "HTML tag/id/class related to the bug (guess from DOM)",
    "suggested_solution": "Technical fix recommendation (e.g., 'Increase padding or remove fixed height')"
  }
]
If there are absolutely no bugs, return an empty array: []
"""

async def analyze_ui(image_path: str, dom_html: str, model_name: str, api_keys: dict):
    try:
        # Temporarily set environment variables for LiteLLM
        for key, value in api_keys.items():
            if value:
                os.environ[key] = value

        base64_image = encode_image(image_path)
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": f"Here is the simplified DOM structure:\n```html\n{dom_html}\n```\nAnalyze the screenshot and DOM for bugs."} ,
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ]
        
        logging.info(f"Sending request to {model_name}...")
        response = await acompletion(
            model=model_name,
            messages=messages,
            temperature=0.1
        )
        
        content = response.choices[0].message.content.strip()
        logging.info(f"AI Response received.")
        
        # Clean up markdown formatting if the AI ignores the system prompt
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        return json.loads(content.strip())
    except Exception as e:
        logging.error(f"AI Analysis failed: {e}")
        return [{"description": f"AI Analysis failed", "element_selector": "N/A", "suggested_solution": str(e)}]
