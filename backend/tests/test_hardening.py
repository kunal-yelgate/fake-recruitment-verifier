import pytest
import httpx
from types import SimpleNamespace
from pydantic import ValidationError

from app import serpapi_client as serpapi_module
from app.models import CheckRequest
from app.serpapi_client import SerpApiClient
from app.cache import QueryCache
from app.main import app as fastapi_app
from app.main import rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request


def test_check_request_rejects_oversized_postings():
    with pytest.raises(ValidationError):
        CheckRequest(raw_text="x" * 10_001)


def test_check_request_accepts_posting_under_limit():
    request = CheckRequest(raw_text="x" * 9_999)

    assert len(request.raw_text) == 9_999


@pytest.mark.parametrize(
    "raw_text, message",
    [
        ("", "cannot be empty"),
        (" " * 10, "cannot be empty"),
        ("x" * 9, "at least 10 characters"),
    ],
)
def test_check_request_rejects_empty_or_too_short_postings(raw_text, message):
    with pytest.raises(ValidationError, match=message):
        CheckRequest(raw_text=raw_text)


@pytest.mark.asyncio
async def test_rate_limit_response_includes_retry_after():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/check",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "scheme": "http",
        "app": fastapi_app,
    }
    request = Request(scope)
    response = await rate_limit_exceeded_handler(
        request,
        RateLimitExceeded(
            SimpleNamespace(error_message=None, limit="10 per 1 minute")
        ),
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_check_requires_authentication(monkeypatch):
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    monkeypatch.setattr("app.config.settings.require_auth", True)
    monkeypatch.setattr("app.config.settings.clerk_jwt_key", None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/check", json={"raw_text": "A valid enough posting text."})

    assert response.status_code == 401
    assert "sign in" in response.json()["detail"].lower()


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


@pytest.mark.asyncio
async def test_mock_mode_keeps_clean_and_gibberish_postings_neutral():
    from app.extraction import extract_fields
    from app.scoring import calculate_risk_score
    from app.signals import evaluate_all_signals

    clean = (
        "Google is hiring a software engineer. Apply through "
        "https://careers.google.com. The role includes standard benefits and interviews."
    )
    clean_fields = await extract_fields(clean)
    clean_score, *_ = calculate_risk_score(await evaluate_all_signals(clean_fields, clean))
    assert clean_score < 65

    gibberish = "qzxv 9182 blorp nnnn"
    gibberish_fields = await extract_fields(gibberish)
    _, verdict, _, _ = calculate_risk_score(
        await evaluate_all_signals(gibberish_fields, gibberish)
    )
    assert verdict == "Insufficient information"


def test_cache_keys_and_storage_exclude_provider_failures(tmp_path):
    query_cache = QueryCache(str(tmp_path / "cache.db"), ttl_hours=24)
    params = {"q": "company", "api_key": "super-secret"}

    key = query_cache.compute_key("google", params)
    assert "super-secret" not in key

    query_cache.set("google", params, {"_source": "error", "_api_error": "quota"})
    assert query_cache.get("google", params) is None


def test_cache_expired_entries_are_removed(tmp_path):
    query_cache = QueryCache(str(tmp_path / "cache.db"), ttl_hours=0)
    params = {"q": "expired"}
    query_cache.set("google", params, {"organic_results": []})

    assert query_cache.get("google", params) is None


@pytest.mark.asyncio
async def test_metrics_endpoint_is_prometheus_compatible():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert "truerecruit_cache_hits_total" in response.text


@pytest.mark.asyncio
async def test_request_id_is_returned_without_logging_request_content():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": "test-request-123"})

    assert response.headers["X-Request-ID"] == "test-request-123"
