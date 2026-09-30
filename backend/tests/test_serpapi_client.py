import httpx
import pytest

from app import serpapi_client as serpapi_module
from app.serpapi_client import SerpApiClient


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.request = httpx.Request("GET", serpapi_module.SERPAPI_ENDPOINT)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", request=self.request, response=self)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeAsyncClient:
    response_factory = None
    calls = 0

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        type(self).calls += 1
        return type(self).response_factory()


class CacheSpy:
    def __init__(self, cached=None):
        self.cached = cached
        self.get_calls = 0
        self.set_calls = []

    def get(self, engine, params):
        self.get_calls += 1
        return self.cached

    def set(self, engine, params, data):
        self.set_calls.append((engine, params, data))


@pytest.mark.asyncio
async def test_serpapi_success_returns_live_result_and_caches(monkeypatch):
    cache = CacheSpy()
    FakeAsyncClient.calls = 0
    FakeAsyncClient.response_factory = lambda: FakeResponse(payload={"organic_results": [{"title": "Acme"}]})
    monkeypatch.setattr(serpapi_module, "cache", cache)
    monkeypatch.setattr(serpapi_module.httpx, "AsyncClient", FakeAsyncClient)

    result = await SerpApiClient(api_key="configured").search("google", {"q": "Acme"})

    assert result["_source"] == "live"
    assert result["_is_mock"] is False
    assert FakeAsyncClient.calls == 1
    assert len(cache.set_calls) == 1


@pytest.mark.asyncio
async def test_serpapi_cache_hit_skips_http(monkeypatch):
    cache = CacheSpy({"organic_results": [], "_source": "live"})
    FakeAsyncClient.calls = 0
    monkeypatch.setattr(serpapi_module, "cache", cache)
    monkeypatch.setattr(serpapi_module.httpx, "AsyncClient", FakeAsyncClient)

    result = await SerpApiClient(api_key="configured").search("google", {"q": "cached"})

    assert result["_source"] == "live"
    assert cache.get_calls == 1
    assert FakeAsyncClient.calls == 0


@pytest.mark.asyncio
async def test_serpapi_401_returns_error_without_retry(monkeypatch):
    FakeAsyncClient.calls = 0
    FakeAsyncClient.response_factory = lambda: FakeResponse(status_code=401)
    monkeypatch.setattr(serpapi_module.cache, "get", lambda *args: None)
    monkeypatch.setattr(serpapi_module.httpx, "AsyncClient", FakeAsyncClient)

    result = await SerpApiClient(api_key="configured").search("google", {"q": "unauthorized"})

    assert result["_source"] == "error"
    assert result["_api_error"] == "SerpApi HTTP 401"
    assert FakeAsyncClient.calls == 1


@pytest.mark.asyncio
async def test_serpapi_429_retries_then_returns_error(monkeypatch):
    FakeAsyncClient.calls = 0
    FakeAsyncClient.response_factory = lambda: FakeResponse(status_code=429)
    monkeypatch.setattr(serpapi_module.cache, "get", lambda *args: None)
    monkeypatch.setattr(serpapi_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(serpapi_module.asyncio, "sleep", lambda *_: _completed_sleep())

    result = await SerpApiClient(api_key="configured").search("google", {"q": "limited"})

    assert result["_source"] == "error"
    assert result["_api_error"] == "SerpApi HTTP 429"
    assert FakeAsyncClient.calls == 3


async def _completed_sleep():
    return None


@pytest.mark.asyncio
async def test_serpapi_timeout_retries_then_returns_error(monkeypatch):
    FakeAsyncClient.calls = 0
    FakeAsyncClient.response_factory = lambda: _raise_timeout()
    monkeypatch.setattr(serpapi_module.cache, "get", lambda *args: None)
    monkeypatch.setattr(serpapi_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(serpapi_module.asyncio, "sleep", lambda *_: _completed_sleep())

    result = await SerpApiClient(api_key="configured").search("google", {"q": "timeout"})

    assert result["_source"] == "error"
    assert result["_api_error"] == "ReadTimeout"
    assert FakeAsyncClient.calls == 3


def _raise_timeout():
    raise httpx.ReadTimeout("request timed out")


@pytest.mark.asyncio
async def test_serpapi_malformed_json_returns_error_without_caching(monkeypatch):
    cache = CacheSpy()
    FakeAsyncClient.calls = 0
    FakeAsyncClient.response_factory = lambda: FakeResponse(payload=ValueError("malformed JSON"))
    monkeypatch.setattr(serpapi_module, "cache", cache)
    monkeypatch.setattr(serpapi_module.httpx, "AsyncClient", FakeAsyncClient)

    result = await SerpApiClient(api_key="configured").search("google", {"q": "bad"})

    assert result["_source"] == "error"
    assert result["_api_error"] == "ValueError"
    assert cache.set_calls == []
