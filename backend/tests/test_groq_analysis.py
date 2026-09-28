"""Tests for grounded Groq decision summaries."""

import json

import pytest

from app import groq_analysis
from app.config import settings
from app.groq_analysis import assess_with_groq
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
        "recommendation": "avoid_contact",
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
    ]

    result = await assess_with_groq(
        "Job offer. Pay the $250 equipment fee upfront.", signals
    )

    assert result is not None
    assert result.recommendation == "avoid_contact"
    assert result.evidence_quotes == ["Pay the $250 equipment fee upfront"]
    submitted_findings = request_body["messages"][1]["content"]
    assert "Official domain does not match" in submitted_findings
    assert "Fake result says" not in submitted_findings


@pytest.mark.asyncio
async def test_groq_decision_rejects_unverifiable_quotes(monkeypatch):
    response_body = {
        "recommendation": "avoid_contact",
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