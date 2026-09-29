import pytest
import httpx
from pydantic import ValidationError

from app import serpapi_client as serpapi_module
from app.models import CheckRequest
from app.serpapi_client import SerpApiClient


def test_check_request_rejects_oversized_postings():
    with pytest.raises(ValidationError):
        CheckRequest(raw_text="x" * 10_001)


@pytest.mark.asyncio
async def test_mock_serpapi_results_are_not_cached(monkeypatch):
    writes = []

    class CacheSpy:
        def get(self, engine, params):
            return None

        def set(self, engine, params, data):
            writes.append(data)

    monkeypatch.setattr("app.serpapi_client.cache", CacheSpy())
    client = SerpApiClient(api_key=None)

    result = await client.search("google", {"q": "demo query"})

    assert result["_source"] == "mock"
    assert writes == []


@pytest.mark.asyncio
async def test_provider_errors_are_not_cached(monkeypatch):
    writes = []

    class CacheSpy:
        def get(self, engine, params):
            return None

        def set(self, engine, params, data):
            writes.append(data)

    class FailingClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, *args, **kwargs):
            response = httpx.Response(
                429,
                request=httpx.Request("GET", "https://serpapi.com/search.json"),
                text="quota exhausted",
            )
            response.raise_for_status()
            return response

    monkeypatch.setattr("app.serpapi_client.cache", CacheSpy())
    monkeypatch.setattr(serpapi_module.httpx, "AsyncClient", FailingClient)
    client = SerpApiClient(api_key="configured")

    result = await client.search("google", {"q": "provider error"})

    assert result["_source"] == "error"
    assert writes == []
