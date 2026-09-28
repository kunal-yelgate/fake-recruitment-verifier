"""Unit tests for structured field extraction engine."""

from pathlib import Path
import json
import pytest
from app import extraction
from app.config import settings
from app.extraction import extract_fields, extract_with_regex

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_extract_scam_posting():
    scam_text = (FIXTURES_DIR / "scam_posting.txt").read_text(encoding="utf-8")
    fields = extract_with_regex(scam_text)

    assert fields.company_name is not None
    assert "Apex Global Staffing" in fields.company_name
    assert fields.recruiter_name == "Marcus Vance"
    assert fields.contact_email == "marcus.vance.careers@gmail.com"
    assert fields.claimed_domain in ("apexglobal-staffing.org", "gmail.com")
    assert fields.job_title is not None
    assert "Data Entry" in fields.job_title
    assert fields.distinctive_phrase is not None
    assert len(fields.distinctive_phrase.split()) >= 6


def test_extract_legit_posting():
    legit_text = (FIXTURES_DIR / "legit_posting.txt").read_text(encoding="utf-8")
    fields = extract_with_regex(legit_text)

    assert fields.company_name is not None
    assert "Stripe" in fields.company_name
    assert fields.contact_email == "talent@stripe.com"
    assert fields.claimed_domain == "stripe.com"
    assert fields.job_title is not None
    assert "Software Engineer" in fields.job_title


def test_extract_fallback_defaults():
    minimal_text = "Join our fast growing startup as a Frontend Developer! Email us at jobs@startup.io"
    fields = extract_with_regex(minimal_text)

    assert fields.contact_email == "jobs@startup.io"
    assert fields.claimed_domain == "startup.io"
    assert fields.distinctive_phrase is not None


def test_extract_website_domain_separately_from_free_email():
    posting = (
        "Company: Acme Labs\nRecruiter: Jamie Smith\n"
        "Email: jamie@gmail.com\nCareers site: https://acmelabs.example/jobs"
    )

    fields = extract_with_regex(posting)

    assert fields.contact_email == "jamie@gmail.com"
    assert fields.claimed_domain == "acmelabs.example"


def test_regex_extracts_salary_and_payment_requests():
    posting = (
        "Acme Labs is hiring a coordinator. Salary: $25 - $30 per hour. "
        "Applicants must pay a $75 background check fee and buy gift cards."
    )

    fields = extract_with_regex(posting)

    assert fields.salary_range == "$25 - $30 per hour"
    assert fields.payment_requests
    assert any("background check fee" in request.lower() for request in fields.payment_requests)
    assert any("gift cards" in request.lower() for request in fields.payment_requests)


@pytest.mark.asyncio
async def test_groq_extraction_uses_only_text_grounded_values(monkeypatch):
    posting = (
        "Senior Data Engineer\nCompany: Acme Labs\nRecruiter: Jamie Smith\n"
        "Email: jamie@acme.example\nWebsite: acme.example\n"
        "We are hiring a Senior Data Engineer to build reliable systems. "
        "Salary: $140,000 - $165,000 per year. Applicants must pay a processing fee."
    )
    response_data = {
        "company_name": "Acme Labs",
        "recruiter_name": "Imaginary Person",
        "claimed_domain": "acme.example",
        "contact_email": "jamie@acme.example",
        "job_title": "Senior Data Engineer",
        "salary_range": "$140,000 - $165,000 per year",
        "payment_requests": ["Applicants must pay a processing fee"],
        "distinctive_phrase": "We are hiring a Senior Data Engineer to build reliable systems.",
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(response_data)}}]}

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
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(extraction.httpx, "AsyncClient", FakeAsyncClient)

    fields = await extract_fields(posting)

    assert fields.extraction_method == "groq"
    assert fields.company_name == "Acme Labs"
    assert fields.recruiter_name != "Imaginary Person"
    assert fields.contact_email == "jamie@acme.example"
    assert fields.salary_range == "$140,000 - $165,000 per year"
    assert fields.payment_requests == ["Applicants must pay a processing fee"]


def test_llm_claimed_domain_does_not_replace_website_with_email_provider():
    posting = "Email: recruiter@gmail.com\nCareers site: https://acme.example/jobs"
    fallback = extract_with_regex(posting)
    fields = extraction._grounded_llm_fields(
        {
            "claimed_domain": "gmail.com",
            "contact_email": "recruiter@gmail.com",
        },
        posting,
        fallback,
        "groq",
    )

    assert fields.claimed_domain == "acme.example"


@pytest.mark.asyncio
async def test_groq_failure_falls_back_to_regex(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "anthropic_api_key", None)

    class FailingAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(extraction.httpx, "AsyncClient", FailingAsyncClient)
    posting = "Stripe is hiring a Software Engineer. Apply at talent@stripe.com"

    fields = await extract_fields(posting)

    assert fields.extraction_method == "regex"
    assert fields.contact_email == "talent@stripe.com"
