"""Tests for the OpenRouter branch of verify_api_key — the tier-based
:free-suffix filtering is the core logic this PR changes."""
import asyncio
import json

import httpx

import providers

AUTH_KEY_URL = "https://openrouter.ai/api/v1/auth/key"
MODELS_URL = "https://openrouter.ai/api/v1/models"

FREE_VISION_MODEL = {
    "id": "google/gemma-4-31b-it:free",
    "name": "Google: Gemma 4 31B (free)",
    "architecture": {"input_modalities": ["image", "text"]},
}
PAID_VISION_MODEL = {
    "id": "openai/gpt-4.1",
    "name": "OpenAI: GPT-4.1",
    "architecture": {"input_modalities": ["image", "text"]},
}
TEXT_ONLY_MODEL = {
    "id": "meta-llama/llama-guard-4-12b",
    "name": "Llama Guard 4 12B",
    "architecture": {"input_modalities": ["text"]},
}
UNNAMED_FREE_VISION_MODEL = {
    "id": "some-org/some-model:free",
    "architecture": {"input_modalities": ["image", "text"]},
}


CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


def _patch_client(monkeypatch, auth_response, models_response=None, probe_responses=None):
    probe_responses = probe_responses or {}

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if url_str == AUTH_KEY_URL:
            return auth_response
        if url_str == MODELS_URL:
            assert models_response is not None, "models endpoint should not be reached"
            return models_response
        if url_str == CHAT_URL:
            payload = json.loads(request.content)
            model_id = payload.get("model")
            if model_id in probe_responses:
                return probe_responses[model_id]
            return httpx.Response(200, json={"choices": []})
        raise AssertionError(f"unexpected request to {request.url}")

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def test_free_tier_key_only_gets_free_suffixed_vision_models(monkeypatch):
    _patch_client(
        monkeypatch,
        auth_response=httpx.Response(200, json={"data": {"is_free_tier": True}}),
        models_response=httpx.Response(
            200, json={"data": [FREE_VISION_MODEL, PAID_VISION_MODEL, TEXT_ONLY_MODEL]}
        ),
    )

    result = asyncio.run(providers.verify_api_key("openrouter", "sk-or-test"))

    assert result["valid"] is True
    ids = [m["id"] for m in result["vision_models"]]
    assert ids == ["openrouter/google/gemma-4-31b-it:free"]


def test_paid_tier_key_excludes_free_suffixed_models(monkeypatch):
    _patch_client(
        monkeypatch,
        auth_response=httpx.Response(200, json={"data": {"is_free_tier": False}}),
        models_response=httpx.Response(
            200, json={"data": [FREE_VISION_MODEL, PAID_VISION_MODEL, TEXT_ONLY_MODEL]}
        ),
    )

    result = asyncio.run(providers.verify_api_key("openrouter", "sk-or-test"))

    assert result["valid"] is True
    ids = [m["id"] for m in result["vision_models"]]
    assert ids == ["openrouter/openai/gpt-4.1"]


def test_falls_back_to_static_list_when_models_endpoint_fails(monkeypatch):
    _patch_client(
        monkeypatch,
        auth_response=httpx.Response(200, json={"data": {"is_free_tier": True}}),
        models_response=httpx.Response(500),
    )

    result = asyncio.run(providers.verify_api_key("openrouter", "sk-or-test"))

    assert result["valid"] is True
    ids = [m["id"] for m in result["vision_models"]]
    assert ids == [m["id"] for m in providers.PROVIDERS["openrouter"]["free_vision_models"]]
    assert all(i.endswith(":free") for i in ids), "fallback must only offer billable-safe models"


def test_invalid_key_short_circuits_before_models_call(monkeypatch):
    _patch_client(monkeypatch, auth_response=httpx.Response(401))

    result = asyncio.run(providers.verify_api_key("openrouter", "sk-or-bad"))

    assert result == {"valid": False, "error": "Invalid API key"}


def test_unnamed_model_display_name_strips_free_suffix(monkeypatch):
    _patch_client(
        monkeypatch,
        auth_response=httpx.Response(200, json={"data": {"is_free_tier": True}}),
        models_response=httpx.Response(200, json={"data": [UNNAMED_FREE_VISION_MODEL]}),
    )

    result = asyncio.run(providers.verify_api_key("openrouter", "sk-or-test"))

    assert result["vision_models"][0]["name"] == "Some Model"


def test_paid_tier_never_probes_chat_completions(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if url_str == AUTH_KEY_URL:
            return httpx.Response(200, json={"data": {"is_free_tier": False}})
        if url_str == MODELS_URL:
            return httpx.Response(200, json={"data": [PAID_VISION_MODEL, TEXT_ONLY_MODEL]})
        raise AssertionError(f"paid-tier verification should not call {request.url}")

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)

    result = asyncio.run(providers.verify_api_key("openrouter", "sk-or-test"))

    assert result["valid"] is True
    ids = [m["id"] for m in result["vision_models"]]
    assert ids == ["openrouter/openai/gpt-4.1"]


def test_free_tier_keeps_model_on_rate_limited_probe(monkeypatch):
    RATE_LIMITED_MODEL = {
        "id": "some-org/rate-limited:free",
        "name": "Rate Limited",
        "architecture": {"input_modalities": ["image", "text"]},
    }
    _patch_client(
        monkeypatch,
        auth_response=httpx.Response(200, json={"data": {"is_free_tier": True}}),
        models_response=httpx.Response(200, json={"data": [RATE_LIMITED_MODEL]}),
        probe_responses={
            "some-org/rate-limited:free": httpx.Response(429, json={"error": "rate limited"}),
        },
    )

    result = asyncio.run(providers.verify_api_key("openrouter", "sk-or-test"))

    assert result["valid"] is True
    ids = [m["id"] for m in result["vision_models"]]
    assert "openrouter/some-org/rate-limited:free" in ids
