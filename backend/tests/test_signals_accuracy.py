"""Unit tests targeting accuracy edge cases, false-positive protection, and in-text threat scanning."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import ExtractedFields
from app.signals import (
    _email_auth_hints,
    _lookalike_reason,
    _lookup_domain_age_days,
    check_company_footprint,
    check_domain_match,
    check_in_text_threats,
    check_linkedin_presence,
    check_news_fraud,
    find_linkedin_referral_leads,
)


@pytest.mark.asyncio
async def test_in_text_threat_scam():
    fields = ExtractedFields(company_name="Acme Corp")
    scam_text = (
        "We need a Data Entry Clerk. We will send you an upfront check deposit of $3,850 "
        "to buy hardware from our vendor. Contact @HR_Marcus on Telegram."
    )
    result = await check_in_text_threats(fields, scam_text)
    assert result.status == "fail"
    assert result.score_delta >= 20
    assert "Check deposit" in result.finding or "interview redirect" in result.finding


@pytest.mark.asyncio
async def test_in_text_threat_clean():
    fields = ExtractedFields(company_name="Stripe")
    legit_text = "Stripe is hiring a Software Engineer. Apply at stripe.com/jobs or email talent@stripe.com."
    result = await check_in_text_threats(fields, legit_text)
    assert result.status == "pass"
    assert result.score_delta < 0


@pytest.mark.asyncio
async def test_india_registration_fee_and_telegram_only_are_flagged():
    fields = ExtractedFields(company_name="Mumbai Staffing")
    result = await check_in_text_threats(
        fields,
        "Pay a refundable registration fee and security deposit. Continue the interview on Telegram only.",
    )
    assert result.status == "fail"
    assert "registration fee" in result.finding.lower()
    assert "telegram-only" in result.finding.lower()


@pytest.mark.asyncio
async def test_email_auth_is_unknown_without_optional_dnspython(monkeypatch):
    import app.signals.domain_email as domain_email

    monkeypatch.setattr(domain_email, "dns", None)
    assert await _email_auth_hints("example.com") == ""


@pytest.mark.asyncio
async def test_news_false_positive_protection(monkeypatch):
    fields = ExtractedFields(company_name="Google")

    # Mock SerpApi response for Google News containing scam-warning article
    async def mock_search(engine, params):
        return {
            "news_results": [
                {
                    "title": "Google warns users about fake job scam impersonating tech recruiters",
                    "snippet": "Security team warns job seekers to protect against fake recruiter outreach.",
                    "source": "TechCrunch",
                    "link": "https://techcrunch.com/google-scam-warning",
                }
            ]
        }

    from app.signals import serpapi_client

    monkeypatch.setattr(serpapi_client, "search", mock_search)

    result = await check_news_fraud(fields)
    assert result.status == "pass"
    assert result.score_delta < 0
    assert (
        "fake scams impersonating" in result.finding.lower() or "no direct fraud complaints" in result.finding.lower()
    )


@pytest.mark.asyncio
async def test_domain_match_job_board_exclusion(monkeypatch):
    fields = ExtractedFields(company_name="Acme Tech", claimed_domain="acmetech.com")

    # Mock google search returning indeed.com as top result, followed by acmetech.com
    async def mock_search(engine, params):
        return {
            "organic_results": [
                {"link": "https://www.indeed.com/cmp/Acme-Tech", "title": "Acme Tech Careers"},
                {"link": "https://acmetech.com", "title": "Acme Tech | Official Corporate Website"},
            ]
        }

    from app.signals import serpapi_client

    monkeypatch.setattr(serpapi_client, "search", mock_search)

    result = await check_domain_match(fields)
    assert result.status == "pass"
    assert result.score_delta == -15
    assert "acmetech.com" in result.finding


def test_lookalike_domain_detects_edit_distance_and_homoglyphs():
    assert _lookalike_reason("paypa1.com", "paypal.com") is not None
    assert _lookalike_reason("pаypal.com", "paypal.com") is not None
    assert _lookalike_reason("paypal.com", "paypal.com") is None


@pytest.mark.asyncio
async def test_rdap_domain_age_is_reported_without_scoring(monkeypatch):
    registered = (datetime.now(timezone.utc) - timedelta(days=42)).isoformat()

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{"eventAction": "registration", "eventDate": registered}]}

    class FakeAsyncClient:
        def __init__(self, timeout, follow_redirects):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            assert url.endswith("/domain/new-company.example")
            return FakeResponse()

    from app import signals

    monkeypatch.setattr(signals.httpx, "AsyncClient", FakeAsyncClient)

    age_days = await _lookup_domain_age_days("new-company.example")

    assert age_days is not None
    assert 41 <= age_days <= 42


@pytest.mark.asyncio
async def test_free_email_still_checks_company_domain(monkeypatch):
    fields = ExtractedFields(
        company_name="Acme Example",
        contact_email="recruiter@gmail.com",
        claimed_domain="acme-example.com",
    )
    search_queries = []

    async def mock_search(engine, params):
        search_queries.append(params["q"])
        return {"organic_results": [{"link": "https://acme-example.com", "title": "Acme Example official site"}]}

    from app import signals

    monkeypatch.setattr(signals.serpapi_client, "search", mock_search)
    monkeypatch.setattr(signals, "_lookup_domain_age_days", _no_domain_age)

    result = await check_domain_match(fields)

    assert search_queries
    assert result.score_delta == 25
    assert "gmail.com" in result.finding
    assert "acme-example.com" in result.finding


@pytest.mark.asyncio
async def test_domain_signal_flags_typo_of_official_domain(monkeypatch):
    fields = ExtractedFields(company_name="PayPal", claimed_domain="paypa1.com")

    async def mock_search(engine, params):
        return {"organic_results": [{"link": "https://paypal.com", "title": "PayPal"}]}

    from app import signals

    monkeypatch.setattr(signals.serpapi_client, "search", mock_search)
    monkeypatch.setattr(signals, "_lookup_domain_age_days", _no_domain_age)

    result = await check_domain_match(fields)

    assert result.score_delta == 22
    assert result.status == "fail"
    assert "lookalike" in result.finding.lower()


@pytest.mark.asyncio
async def test_domain_signal_uses_groq_selected_live_candidate(monkeypatch):
    fields = ExtractedFields(company_name="Acme Labs", claimed_domain="acme-jobs.example")

    async def mock_search(engine, params):
        return {
            "_source": "live",
            "organic_results": [
                {
                    "link": "https://unrelated.example",
                    "title": "Acme listings directory",
                    "snippet": "Third-party job listings",
                },
                {
                    "link": "https://www.acmelabs.example/about",
                    "title": "Acme Labs | Official Company Website",
                    "snippet": "About Acme Labs",
                },
            ],
        }

    async def mock_groq_selection(company, candidates):
        assert company == "Acme Labs"
        assert len(candidates) == 2
        return "acmelabs.example", "Acme Labs | Official Company Website"

    from app import signals

    monkeypatch.setattr(signals.serpapi_client, "search", mock_search)
    monkeypatch.setattr(signals, "select_official_domain_with_groq", mock_groq_selection)
    monkeypatch.setattr(signals, "_lookup_domain_age_days", _no_domain_age)

    result = await check_domain_match(fields)

    assert result.evidence_url == "https://www.acmelabs.example/about"
    assert "acmelabs.example" in result.finding
    assert "Groq selected this live result" in result.finding


@pytest.mark.asyncio
async def test_linkedin_referral_leads_require_live_company_matched_profiles(monkeypatch):
    fields = ExtractedFields(company_name="Acme Labs")

    async def mock_search(engine, params):
        assert 'site:linkedin.com/in "Acme Labs"' in params["q"]
        return {
            "_source": "live",
            "organic_results": [
                {
                    "link": "https://www.linkedin.com/in/jane-smith?trk=search",
                    "title": "Jane Smith - Recruiter at Acme Labs | LinkedIn",
                    "snippet": "Talent acquisition at Acme Labs.",
                },
                {
                    "link": "https://www.linkedin.com/in/other-person",
                    "title": "Alex Doe - Recruiter",
                    "snippet": "Works at Other Company.",
                },
                {
                    "link": "https://linkedin.com.evil.example/in/fake",
                    "title": "Fake - Acme Labs recruiter",
                    "snippet": "Acme Labs",
                },
            ],
        }

    from app import signals

    monkeypatch.setattr(signals.serpapi_client, "search", mock_search)

    leads = await find_linkedin_referral_leads(fields)

    assert len(leads) == 1
    assert leads[0].name.startswith("Jane Smith")
    assert leads[0].profile_url == "https://www.linkedin.com/in/jane-smith"


@pytest.mark.asyncio
async def test_linkedin_referral_search_ignores_mock_results(monkeypatch):
    fields = ExtractedFields(company_name="Acme Labs")

    async def mock_search(engine, params):
        return {
            "_source": "mock",
            "organic_results": [
                {
                    "link": "https://www.linkedin.com/in/fake-person",
                    "title": "Fake Person - Recruiter at Acme Labs",
                    "snippet": "Recruiter at Acme Labs",
                }
            ],
        }

    from app import signals

    monkeypatch.setattr(signals.serpapi_client, "search", mock_search)

    assert await find_linkedin_referral_leads(fields) == []


async def _no_domain_age(domain):
    return None


@pytest.mark.asyncio
async def test_undisclosed_company_handling():
    fields = ExtractedFields(company_name="Undisclosed Company")
    footprint = await check_company_footprint(fields)
    linkedin = await check_linkedin_presence(fields)

    assert footprint.status == "warning"
    assert footprint.score_delta == 0
    assert linkedin.status == "warning"
    assert linkedin.score_delta == 0


@pytest.mark.asyncio
async def test_search_provider_error_is_neutral(monkeypatch):
    """Provider fallback data must not be scored as search evidence."""
    fields = ExtractedFields(company_name="Acme Corp")

    async def mock_search(engine, params):
        return {"_source": "error", "_api_error": "SerpApi HTTP 429"}

    from app.signals import serpapi_client

    monkeypatch.setattr(serpapi_client, "search", mock_search)

    result = await check_company_footprint(fields)

    assert result.status == "warning"
    assert result.score_delta == 0
    assert result.data_source == "error"
    assert "unavailable" in result.finding.lower()
