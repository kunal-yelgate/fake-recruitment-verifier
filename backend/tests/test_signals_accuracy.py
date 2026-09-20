"""Unit tests targeting accuracy edge cases, false-positive protection, and in-text threat scanning."""

import pytest
from app.models import ExtractedFields
from app.signals import (
    check_in_text_threats,
    check_news_fraud,
    check_domain_match,
    check_company_footprint,
    check_linkedin_presence,
    evaluate_all_signals,
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
    legit_text = (
        "Stripe is hiring a Software Engineer. Apply at stripe.com/jobs or email talent@stripe.com."
    )
    result = await check_in_text_threats(fields, legit_text)
    assert result.status == "pass"
    assert result.score_delta < 0


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
    assert "fake scams impersonating" in result.finding.lower() or "no direct fraud complaints" in result.finding.lower()


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


@pytest.mark.asyncio
async def test_undisclosed_company_handling():
    fields = ExtractedFields(company_name="Undisclosed Company")
    footprint = await check_company_footprint(fields)
    linkedin = await check_linkedin_presence(fields)

    assert footprint.status == "warning"
    assert footprint.score_delta == 0
    assert linkedin.status == "warning"
    assert linkedin.score_delta == 0
