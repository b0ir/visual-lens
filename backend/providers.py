"""
Provider Registry for VisualLens.

Defines all supported AI providers, their vision-capable models,
and key verification logic. This is the single source of truth
for provider configuration.
"""

import httpx
import logging
import re
from litellm import supports_vision

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _display_name(raw_id: str) -> str:
    """Generate a human-readable display name from a raw model ID."""
    name = raw_id
    # Strip trailing date stamps like -2024-11-20 or -20241120
    name = re.sub(r'[-_]\d{4}-\d{2}-\d{2}$', '', name)
    name = re.sub(r'[-_]\d{8}$', '', name)
    # Drop provider prefix (e.g. "meta/" from "meta/llama-...")
    if '/' in name:
        name = name.rsplit('/', 1)[-1]
    name = name.replace('-', ' ').replace('_', ' ')
    parts = []
    for p in name.split():
        if p.lower() == 'gpt':
            parts.append('GPT')
        elif p.lower() == 'ai':
            parts.append('AI')
        else:
            parts.append(p.title())
    return ' '.join(parts)


# claude-3.x and claude-(opus|sonnet|haiku)-4+ all support vision.
_ANTHROPIC_VISION_RE = re.compile(
    r'claude-(?:3|opus-[4-9]|sonnet-[4-9]|haiku-[4-9])'
)


PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "website": "https://platform.openai.com/api-keys",
        "description": "GPT-4.1, o4-mini, and more",
        "vision_models": [
            {"id": "openai/gpt-4.1", "name": "GPT-4.1"},
            {"id": "openai/gpt-4.1-mini", "name": "GPT-4.1 Mini"},
            {"id": "openai/gpt-4.1-nano", "name": "GPT-4.1 Nano"},
            {"id": "openai/gpt-4o", "name": "GPT-4o"},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "openai/o4-mini", "name": "o4-mini"},
        ],
    },
    "anthropic": {
        "name": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "website": "https://console.anthropic.com/settings/keys",
        "description": "Claude Opus, Sonnet, Haiku",
        "vision_models": [
            {"id": "anthropic/claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
            {"id": "anthropic/claude-haiku-3.5", "name": "Claude Haiku 3.5"},
        ],
    },
    "gemini": {
        "name": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "website": "https://aistudio.google.com/apikey",
        "description": "Gemini 2.5 Flash, Pro, and more",
        "vision_models": [
            {"id": "gemini/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "gemini/gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
            {"id": "gemini/gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        ],
    },
    "deepseek": {
        "name": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "website": "https://platform.deepseek.com/api_keys",
        "description": "DeepSeek Chat with vision",
        "vision_models": [
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat (V3)"},
        ],
    },
    "xai": {
        "name": "xAI",
        "env_key": "XAI_API_KEY",
        "website": "https://console.x.ai/",
        "description": "Grok vision models",
        "vision_models": [
            {"id": "xai/grok-2-vision-latest", "name": "Grok 2 Vision"},
        ],
    },
    "openrouter": {
        "name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "website": "https://openrouter.ai/keys",
        "description": "100+ models via one key — free tier available",
        "vision_models": [
            {"id": "openrouter/google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "openrouter/anthropic/claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
            {"id": "openrouter/openai/gpt-4.1", "name": "GPT-4.1"},
            {"id": "openrouter/meta-llama/llama-4-maverick", "name": "Llama 4 Maverick"},
            {"id": "openrouter/qwen/qwen-2.5-vl-72b-instruct", "name": "Qwen 2.5 VL 72B"},
        ],
        # Models accessible without credits (OpenRouter :free-tier variants).
        # These use the :free suffix which routes to providers that sponsor free access.
        "free_vision_models": [
            {"id": "openrouter/meta-llama/llama-4-maverick", "name": "Llama 4 Maverick (Free)"},
            {"id": "openrouter/meta-llama/llama-4-scout", "name": "Llama 4 Scout (Free)"},
        ],
    },
    "nvidia": {
        "name": "NVIDIA",
        "env_key": "NVIDIA_API_KEY",
        "website": "https://build.nvidia.com/",
        "description": "NVIDIA NIM vision models",
        "vision_models": [
            {"id": "nvidia_nim/meta/llama-3.2-90b-vision-instruct", "name": "Llama 3.2 90B Vision"},
            {"id": "nvidia_nim/meta/llama-3.2-11b-vision-instruct", "name": "Llama 3.2 11B Vision"},
        ],
    },
}


async def verify_api_key(provider_id: str, api_key: str) -> dict:
    """
    Verify an API key by making a lightweight call to the provider.
    Returns {"valid": True/False, "error": "..." if invalid}.
    """
    if provider_id not in PROVIDERS:
        return {"valid": False, "error": f"Unknown provider: {provider_id}"}

    if not api_key or not api_key.strip():
        return {"valid": False, "error": "API key cannot be empty"}

    api_key = api_key.strip()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if provider_id == "openai":
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    raw = resp.json().get("data", [])
                    vision = sorted(
                        [
                            {"id": f"openai/{m['id']}", "name": _display_name(m["id"])}
                            for m in raw
                            if supports_vision(f"openai/{m['id']}")
                        ],
                        key=lambda x: x["id"],
                    )
                    return {
                        "valid": True,
                        "vision_models": vision or PROVIDERS["openai"]["vision_models"],
                    }
                return {"valid": False, "error": "Invalid API key or insufficient permissions"}

            elif provider_id == "anthropic":
                resp = await client.get(
                    "https://api.anthropic.com/v1/models?limit=100",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                if resp.status_code == 200:
                    raw = resp.json().get("data", [])
                    vision = sorted(
                        [
                            {
                                "id": f"anthropic/{m['id']}",
                                "name": m.get("display_name") or _display_name(m["id"]),
                            }
                            for m in raw
                            if _ANTHROPIC_VISION_RE.search(m.get("id", ""))
                        ],
                        key=lambda x: x["id"],
                        reverse=True,
                    )
                    return {
                        "valid": True,
                        "vision_models": vision or PROVIDERS["anthropic"]["vision_models"],
                    }
                if resp.status_code == 401:
                    return {"valid": False, "error": "Invalid API key"}
                return {"valid": False, "error": f"Unexpected response (status {resp.status_code})"}

            elif provider_id == "gemini":
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}&pageSize=100"
                )
                if resp.status_code == 200:
                    raw = resp.json().get("models", [])
                    vision = []
                    for m in raw:
                        raw_id = m.get("name", "").removeprefix("models/")
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" not in methods:
                            continue
                        if any(skip in raw_id for skip in ("embedding", "aqa")):
                            continue
                        # gemini-1.5+ and gemini-2.x support multimodal inputs;
                        # older gemini-1.0 models are text-only except the explicit -vision variant.
                        if not re.search(r'gemini-(1\.5|2)', raw_id) and "vision" not in raw_id:
                            continue
                        display = m.get("displayName") or _display_name(raw_id)
                        vision.append({"id": f"gemini/{raw_id}", "name": display})
                    vision.sort(key=lambda x: x["id"], reverse=True)
                    return {
                        "valid": True,
                        "vision_models": vision or PROVIDERS["gemini"]["vision_models"],
                    }
                return {"valid": False, "error": "Invalid API key"}

            elif provider_id == "deepseek":
                resp = await client.get(
                    "https://api.deepseek.com/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    raw = resp.json().get("data", [])
                    # deepseek-chat (V3) supports image inputs; deepseek-reasoner (R1) is text-only.
                    vision = [
                        {"id": f"deepseek/{m['id']}", "name": _display_name(m["id"])}
                        for m in raw
                        if "chat" in m.get("id", "").lower()
                    ]
                    return {
                        "valid": True,
                        "vision_models": vision or PROVIDERS["deepseek"]["vision_models"],
                    }
                return {"valid": False, "error": "Invalid API key"}

            elif provider_id == "xai":
                resp = await client.get(
                    "https://api.x.ai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    raw = resp.json().get("data", [])
                    vision = sorted(
                        [
                            {"id": f"xai/{m['id']}", "name": _display_name(m["id"])}
                            for m in raw
                            if "vision" in m.get("id", "").lower()
                        ],
                        key=lambda x: x["id"],
                        reverse=True,
                    )
                    return {
                        "valid": True,
                        "vision_models": vision or PROVIDERS["xai"]["vision_models"],
                    }
                return {"valid": False, "error": "Invalid API key"}

            elif provider_id == "openrouter":
                resp = await client.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    key_data = resp.json().get("data", {})
                    is_free_tier = key_data.get("is_free_tier", False)
                    models_key = "free_vision_models" if is_free_tier else "vision_models"
                    return {
                        "valid": True,
                        "vision_models": PROVIDERS["openrouter"].get(models_key, PROVIDERS["openrouter"]["vision_models"]),
                    }
                return {"valid": False, "error": "Invalid API key"}

            elif provider_id == "nvidia":
                resp = await client.get(
                    "https://integrate.api.nvidia.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    raw = resp.json().get("data", [])
                    vision = sorted(
                        [
                            {"id": f"nvidia_nim/{m['id']}", "name": _display_name(m["id"])}
                            for m in raw
                            if "vision" in m.get("id", "").lower()
                        ],
                        key=lambda x: x["id"],
                    )
                    return {
                        "valid": True,
                        "vision_models": vision or PROVIDERS["nvidia"]["vision_models"],
                    }
                return {"valid": False, "error": "Invalid API key"}

            else:
                return {"valid": False, "error": f"Verification not supported for provider: {provider_id}"}

    except httpx.TimeoutException:
        return {"valid": False, "error": "Connection timed out. Check your network connection."}
    except Exception as e:
        logger.error(f"Key verification failed for {provider_id}: {e}")
        return {"valid": False, "error": "Verification failed. Check your network connection and API key."}


def get_providers_catalog() -> dict:
    """
    Return the full provider catalog for the frontend.
    Strips internal fields like env_key.
    """
    catalog = {}
    for pid, pdata in PROVIDERS.items():
        catalog[pid] = {
            "name": pdata["name"],
            "description": pdata["description"],
            "website": pdata["website"],
            "vision_models": pdata["vision_models"],
        }
    return catalog


def get_env_key_name(provider_id: str) -> str:
    """Get the environment variable name for a provider's API key."""
    if provider_id in PROVIDERS:
        return PROVIDERS[provider_id]["env_key"]
    return ""
