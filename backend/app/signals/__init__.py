"""Compatibility facade for signal evaluators.

The public ``app.signals`` imports remain stable while each evaluator lives in
its own focused module.
"""

import asyncio
import re
from typing import List

import httpx

from app.config import settings
from app.groq_analysis import select_official_domain_with_groq
from app.models import ExtractedFields, SignalResult
from app.serpapi_client import serpapi_client

from .company_footprint import check_company_footprint
from .domain_email import check_domain_match
from .domain_email import _email_auth_hints
from .duplicate_posting import check_duplicate_posting
from .linkedin import check_linkedin_presence
from .linkedin_referrals import find_linkedin_referral_leads
from .news_fraud import check_news_fraud
from .recruiter_identity import check_recruiter_identity
from .shared import (
    FREE_EMAIL_DOMAINS,
    JOB_PLATFORM_DOMAINS,
    _domain_brand_label,
    _extract_domain_from_url,
    _levenshtein_distance,
    _lookalike_reason,
    _lookup_domain_age_days,
    _registrable_domain,
    _unavailable_search_signal,
)
from .text_threats import check_in_text_threats


async def evaluate_all_signals(fields: ExtractedFields, raw_text: str = "") -> list[SignalResult]:
    """Run all 7 SerpApi & text forensic verification signals concurrently."""
    tasks = [
        check_in_text_threats(fields, raw_text),
        check_company_footprint(fields),
        check_linkedin_presence(fields),
        check_duplicate_posting(fields),
        check_news_fraud(fields),
        check_domain_match(fields),
        check_recruiter_identity(fields),
    ]
    results: list[SignalResult] = await asyncio.gather(*tasks)
    if len(re.findall(r"\b\w+\b", raw_text)) < 6:
        for result in results:
            result.score_delta = 0
            result.status = "unknown"
            result.finding = "Insufficient information to evaluate this posting."
        return results
    has_live_key = bool(settings.serpapi_key and settings.serpapi_key.strip() not in ("", "your_serpapi_key_here"))
    if not has_live_key:
        for result in results:
            if result.engine != "nlp_regex" and result.data_source == "live":
                result.data_source = "mock"
    return results
