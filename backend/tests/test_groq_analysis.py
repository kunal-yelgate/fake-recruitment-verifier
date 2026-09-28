"""Tests for grounded Groq decision summaries."""

import json

import pytest

from app import groq_analysis
from app.config import settings
from app.groq_analysis import assess_with_groq, select_official_domain_with_groq
from app.models import SignalResult


def make_signal(source: str, finding: str) -> SignalResult:
    return SignalResult(
        signal_key="test_signal",
        signal_name="Test Signal",
        engine="google",
        score_delta=0,
        status="warning",
        finding=finding,
        query_used="test query",
        evidence_url=None,
        search_url=None,
        data_source=source,
    )


@pytest.mark.asyncio
async def test_groq_decision_uses_live_evidence_and_validates_quotes(monkeypatch):
    response_body = {
        "recommendation": "do_not_apply",
        "explanation": "The posting asks the candidate to pay an upfront fee.",
        "evidence_quotes": ["Pay the $250 equipment fee upfront"],
    }
    request_body = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(response_body)}}]}

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, headers, json):
            request_body.update(json)
            return FakeResponse()

    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(groq_analysis.httpx, "AsyncClient", FakeAsyncClient)
    signals = [
        make_signal("live", "Official domain does not match the recruiter email."),
        make_signal("mock", "Fake result says the company is fraudulent."),
        SignalResult(
            signal_key="text_threat_signals",
            signal_name="In-Posting Threat Patterns",
            engine="nlp_regex",
            score_delta=25,
            status="fail",
            finding="The posting requests an upfront fee.",
            query_used="text scan",
            evidence_url=None,
            search_url=None,
            data_source="text",
        ),
    ]

    result = await assess_with_groq(
        "Job offer. Pay the $250 equipment fee upfront.", signals
    )

    assert result is not None
    assert result.recommendation == "do_not_apply"
    assert result.evidence_quotes == ["Pay the $250 equipment fee upfront"]
    submitted_findings = request_body["messages"][1]["content"]
    assert "Official domain does not match" in submitted_findings
    assert "Fake result says" not in submitted_findings


@pytest.mark.asyncio
async def test_groq_decision_rejects_unverifiable_quotes(monkeypatch):
    response_body = {
        "recommendation": "do_not_apply",
        "explanation": "The recruiter requests sensitive information.",
        "evidence_quotes": ["Send your bank password immediately"],
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(response_body)}}]}

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(groq_analysis.httpx, "AsyncClient", FakeAsyncClient)

    result = await assess_with_groq("A normal job posting.", [])

    assert result is None


@pytest.mark.asyncio
async def test_groq_selects_only_a_cited_serp_candidate(monkeypatch):
    response_body = {
        "candidate_index": 1,
        "evidence": "Acme Labs | Official Company Website",
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(response_body)}}]}

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(groq_analysis.httpx, "AsyncClient", FakeAsyncClient)
    candidates = [
        {
            "candidate_index": 0,
            "domain": "acme-careers-example.com",
            "link": "https://acme-careers-example.com",
            "title": "Acme careers portal",
            "snippet": "Third-party jobs listing",
        },
        {
            "candidate_index": 1,
            "domain": "acme.example",
            "link": "https://www.acme.example/about",
            "title": "Acme Labs | Official Company Website",
            "snippet": "About Acme Labs",
        },
    ]

    result = await select_official_domain_with_groq("Acme Labs", candidates)

    assert result == ("acme.example", "Acme Labs | Official Company Website")


@pytest.mark.asyncio
async def test_groq_domain_selection_rejects_unquoted_evidence(monkeypatch):
    response_body = {"candidate_index": 0, "evidence": "Acme Labs is verified"}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(response_body)}}]}

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(groq_analysis.httpx, "AsyncClient", FakeAsyncClient)
    candidates = [{
        "candidate_index": 0,
        "domain": "acme.example",
        "link": "https://acme.example",
        "title": "Acme site",
        "snippet": "Products and careers",
    }]

    result = await select_official_domain_with_groq("Acme Labs", candidates)

    assert result is None