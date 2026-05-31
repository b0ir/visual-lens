"""Smoke tests for the SSRF guard in main._check_ssrf."""
import pytest

from main import _check_ssrf


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://127.0.0.1:8000/path",
        "http://10.0.0.5",
        "http://192.168.1.1",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://localhost:8000",
        "http://app.localhost",
    ],
)
def test_blocks_private_and_loopback(url):
    with pytest.raises(ValueError):
        _check_ssrf(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "https://example.com/some/page?q=1",
    ],
)
def test_allows_public_hosts(url):
    # Should not raise.
    _check_ssrf(url)


def test_rejects_missing_host():
    with pytest.raises(ValueError):
        _check_ssrf("http:///no-host")


def test_unresolvable_host_is_allowed_through():
    # An unresolvable name must not raise; the browser surfaces the failure.
    _check_ssrf("https://nonexistent-host-visuallens.invalid")
