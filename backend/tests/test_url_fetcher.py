import ipaddress

import httpx
import pytest

from app import url_fetcher
from app.url_fetcher import (
    InvalidURL,
    URLFetchTooLarge,
    URLFetchUnsupportedContent,
    fetch_text,
    validate_url,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/job",
        "http://127.0.0.1/job",
        "http://[::1]/job",
        "http://169.254.169.254/latest",
        "http://10.0.0.4/job",
    ],
)
async def test_validate_url_rejects_unsafe_schemes_and_ip_literals(url):
    with pytest.raises(InvalidURL):
        await validate_url(url)


@pytest.mark.asyncio
async def test_validate_url_rejects_any_private_dns_result(monkeypatch):
    async def resolve(hostname, port):
        del hostname, port
        for address in ("203.0.113.10", "192.168.1.5"):
            if ipaddress.ip_address(address).is_private:
                raise InvalidURL("private")

    monkeypatch.setattr(url_fetcher, "_resolve_public_addresses", resolve)
    with pytest.raises(InvalidURL):
        await validate_url("https://job.example.test/posting")


class _FakeStream:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _FakeClient:
    responses = []

    def __init__(self, **kwargs):
        del kwargs
        self._responses = iter(self.responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def stream(self, method, url):
        assert method == "GET"
        response = next(self._responses)
        response.request = httpx.Request(method, url)
        return _FakeStream(response)


def _response(status_code, *, headers=None, content=b"posting text"):
    return httpx.Response(status_code, headers=headers or {}, content=content)


@pytest.mark.asyncio
async def test_fetch_text_follows_bounded_redirects_and_returns_text(monkeypatch):
    async def public_dns(hostname, port):
        del hostname, port

    _FakeClient.responses = [
        _response(302, headers={"location": "https://jobs.example.test/final"}),
        _response(200, headers={"content-type": "text/html; charset=utf-8"}, content=b"<h1>Role</h1>"),
    ]
    monkeypatch.setattr(url_fetcher, "_resolve_public_addresses", public_dns)
    monkeypatch.setattr(url_fetcher.httpx, "AsyncClient", _FakeClient)

    result = await fetch_text("https://jobs.example.test/start", max_redirects=1)

    assert result.text == "<h1>Role</h1>"
    assert result.final_url == "https://jobs.example.test/final"
    assert result.content_type == "text/html"


@pytest.mark.asyncio
async def test_fetch_text_enforces_content_type_and_streaming_size(monkeypatch):
    async def public_dns(hostname, port):
        del hostname, port

    monkeypatch.setattr(url_fetcher, "_resolve_public_addresses", public_dns)
    monkeypatch.setattr(url_fetcher.httpx, "AsyncClient", _FakeClient)

    _FakeClient.responses = [
        _response(200, headers={"content-type": "application/pdf"}, content=b"pdf"),
    ]
    with pytest.raises(URLFetchUnsupportedContent):
        await fetch_text("https://jobs.example.test/file")

    _FakeClient.responses = [
        _response(200, headers={"content-type": "text/plain"}, content=b"0123456789"),
    ]
    with pytest.raises(URLFetchTooLarge):
        await fetch_text("https://jobs.example.test/file", max_bytes=5)
