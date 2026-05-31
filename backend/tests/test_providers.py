"""Smoke tests for the provider catalog shape."""
from providers import get_providers_catalog


def test_catalog_is_non_empty_dict():
    catalog = get_providers_catalog()
    assert isinstance(catalog, dict)
    assert catalog, "provider catalog should not be empty"


def test_every_provider_has_required_fields():
    catalog = get_providers_catalog()
    for pid, provider in catalog.items():
        assert provider.get("name"), f"{pid} missing name"
        assert isinstance(provider.get("vision_models"), list)
        assert provider["vision_models"], f"{pid} has no vision models"


def test_every_vision_model_has_id_and_name():
    catalog = get_providers_catalog()
    for pid, provider in catalog.items():
        for model in provider["vision_models"]:
            assert model.get("id"), f"{pid} model missing id"
            assert model.get("name"), f"{pid} model {model.get('id')} missing name"


def test_catalog_strips_internal_env_key():
    catalog = get_providers_catalog()
    for pid, provider in catalog.items():
        assert "env_key" not in provider, f"{pid} leaks internal env_key"
