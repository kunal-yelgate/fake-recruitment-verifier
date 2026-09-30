"""Duplicate posting signal."""

import urllib.parse

from app.models import ExtractedFields, SignalResult
from app.serpapi_client import serpapi_client

from .shared import _extract_domain_from_url, _unavailable_search_signal


async def check_duplicate_posting(fields: ExtractedFields) -> SignalResult:
    """Check 4: Exact phrase search to spot cross-posting spam or scraper fingerprint."""
    phrase = fields.distinctive_phrase or "hiring remote immediate"
    query = f'"{phrase}"'
    params = {"q": query}
    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

    data = await serpapi_client.search("google", params)
    unavailable = _unavailable_search_signal(data, "Duplicate / Cross-Posting Fingerprint", "google", query, search_url)
    if unavailable:
        unavailable.signal_key = "duplicate_posting"
        return unavailable
    organic = data.get("organic_results", [])
    count = len(organic)

    # Check if duplicate is on pastebins or known suspicious boards
    suspicious_domains = {"pastebin.com", "telegra.ph", "freelance-jobs.xyz", "classifieds-spam.net", "forum"}
    suspicious_count = 0
    top_link = None

    for item in organic:
        link = item.get("link", "")
        if not top_link:
            top_link = link
        domain = _extract_domain_from_url(link)
        if any(s in domain for s in suspicious_domains):
            suspicious_count += 1

    if count >= 4 or suspicious_count >= 1:
        return SignalResult(
            signal_key="duplicate_posting",
            signal_name="Duplicate / Cross-Posting Fingerprint",
            engine="google",
            score_delta=18,
            status="fail",
            finding=f"Exact posting text was duplicated across {count} different websites/forums (typical signature of automated recruitment spam).",
            query_used=query,
            evidence_url=top_link or search_url,
            search_url=search_url,
        )
    elif count == 1:
        return SignalResult(
            signal_key="duplicate_posting",
            signal_name="Duplicate / Cross-Posting Fingerprint",
            engine="google",
            score_delta=-8,
            status="pass",
            finding="Posting text is unique and appears restricted to official recruitment channels.",
            query_used=query,
            evidence_url=top_link or search_url,
            search_url=search_url,
        )

    return SignalResult(
        signal_key="duplicate_posting",
        signal_name="Duplicate / Cross-Posting Fingerprint",
        engine="google",
        score_delta=-4,
        status="pass",
        finding="No widespread duplicate spam copies found across public forums or paste sites.",
        query_used=query,
        evidence_url=search_url,
        search_url=search_url,
    )
