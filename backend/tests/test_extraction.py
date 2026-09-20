"""Unit tests for structured field extraction engine."""

from pathlib import Path
import pytest
from app.extraction import extract_with_regex

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
