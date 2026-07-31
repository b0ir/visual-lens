"""Tests for the NVIDIA NIM branch of verify_api_key — probing model endpoints and filtering out 404 models."""
import asyncio
import json
import httpx
import providers

MODELS_URL = "https://integrate.api.nvidia.com/v1/models"
CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

VALID_VISION_MODEL = {"id": "meta/llama-3.2-11b-vision-instruct"}
DEPRECATED_404_MODEL = {"id": "microsoft/phi-3-vision-128k-instruct"}
TEXT_ONLY_MODEL = {"id": "meta/llama-3.1-8b-instruct"}


def _patch_client(monkeypatch, models_response, probe_responses=None):
    probe_responses = probe_responses or {}

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if url_str == MODELS_URL:
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


def test_nvidia_filters_out_404_deprecated_models(monkeypatch):
    _patch_client(
        monkeypatch,
        models_response=httpx.Response(
            200, json={"data": [VALID_VISION_MODEL, DEPRECATED_404_MODEL, TEXT_ONLY_MODEL]}
        ),
        probe_responses={
            "meta/llama-3.2-11b-vision-instruct": httpx.Response(200, json={"choices": []}),
            "microsoft/phi-3-vision-128k-instruct": httpx.Response(
                404, json={"status": 404, "title": "Not Found", "detail": "Function not found"}
            ),
        },
    )

    result = asyncio.run(providers.verify_api_key("nvidia", "nvapi-test"))

    assert result["valid"] is True
    ids = [m["id"] for m in result["vision_models"]]
    assert "nvidia_nim/meta/llama-3.2-11b-vision-instruct" in ids
    assert "nvidia_nim/microsoft/phi-3-vision-128k-instruct" not in ids


def test_nvidia_invalid_key_returns_error(monkeypatch):
    _patch_client(monkeypatch, models_response=httpx.Response(401))

    result = asyncio.run(providers.verify_api_key("nvidia", "nvapi-bad"))

    assert result == {"valid": False, "error": "Invalid API key"}
