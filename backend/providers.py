"""
Provider Registry for VisualLens.

Defines all supported AI providers, their vision-capable models,
and key verification logic. This is the single source of truth
for provider configuration.
"""

import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        "description": "Access 100+ models with one key",
        "vision_models": [
            {"id": "openrouter/google/gemini-2.5-flash", "name": "Gemini 2.5 Flash (via OpenRouter)"},
            {"id": "openrouter/anthropic/claude-sonnet-4-6", "name": "Claude Sonnet 4.6 (via OpenRouter)"},
            {"id": "openrouter/openai/gpt-4.1", "name": "GPT-4.1 (via OpenRouter)"},
            {"id": "openrouter/meta-llama/llama-4-maverick", "name": "Llama 4 Maverick (via OpenRouter)"},
            {"id": "openrouter/qwen/qwen-2.5-vl-72b-instruct", "name": "Qwen 2.5 VL 72B (via OpenRouter)"},
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
                    return {"valid": True}
                return {"valid": False, "error": "Invalid API key or insufficient permissions"}

            elif provider_id == "anthropic":
                # Anthropic doesn't have a lightweight list endpoint,
                # so we send a minimal messages request that will validate auth.
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-3.5",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                # 200 = valid (we got a response), 401 = bad key
                if resp.status_code in (200, 400):
                    # 400 can mean the request was valid auth-wise but bad params
                    return {"valid": True}
                if resp.status_code == 401:
                    return {"valid": False, "error": "Invalid API key"}
                return {"valid": False, "error": f"Unexpected response (status {resp.status_code})"}

            elif provider_id == "gemini":
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                )
                if resp.status_code == 200:
                    return {"valid": True}
                return {"valid": False, "error": "Invalid API key"}

            elif provider_id == "deepseek":
                resp = await client.get(
                    "https://api.deepseek.com/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    return {"valid": True}
                return {"valid": False, "error": "Invalid API key"}

            elif provider_id == "xai":
                resp = await client.get(
                    "https://api.x.ai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    return {"valid": True}
                return {"valid": False, "error": "Invalid API key"}

            elif provider_id == "openrouter":
                resp = await client.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    return {"valid": True}
                return {"valid": False, "error": "Invalid API key"}

            else:
                return {"valid": False, "error": f"Verification not supported for provider: {provider_id}"}

    except httpx.TimeoutException:
        return {"valid": False, "error": "Connection timed out. Check your network connection."}
    except Exception as e:
        logger.error(f"Key verification failed for {provider_id}: {e}")
        return {"valid": False, "error": f"Verification failed: {str(e)}"}


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
