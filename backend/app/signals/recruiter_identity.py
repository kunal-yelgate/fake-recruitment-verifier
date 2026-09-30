"""Recruiter identity signal."""

import urllib.parse

from app.models import ExtractedFields, SignalResult
from app.serpapi_client import serpapi_client

from .shared import _unavailable_search_signal


async def check_recruiter_identity(fields: ExtractedFields) -> SignalResult:
    """Check 7: Recruiter identity & company affiliation verification."""
    recruiter = fields.recruiter_name
    company = fields.company_name or ""

    if not recruiter or not company or company == "Undisclosed Company":
        return SignalResult(
            signal_key="recruiter_check",
            signal_name="Recruiter Identity Verification",
            engine="google",
            score_delta=0,
            status="warning",
            finding="No specific recruiter or hiring manager name found in the posting text.",
            query_used="N/A",
            evidence_url=None,
            search_url=None,
        )

    query = f'"{recruiter}" "{company}" (recruiter OR talent OR HR OR "human resources" OR linkedin)'
    params = {"q": query}
    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    data = await serpapi_client.search("google", params)
    unavailable = _unavailable_search_signal(data, "Recruiter Identity Verification", "google", query, search_url)
    if unavailable:
        unavailable.signal_key = "recruiter_check"
        return unavailable
    organic = data.get("organic_results", [])

    recruiter_parts = recruiter.lower().split()
    company_clean = "".join(c for c in company.lower() if c.isalnum() or c.isspace())
    company_parts = [
        p
        for p in company_clean.split()
        if p not in {"inc", "llc", "corp", "ltd", "group", "co", "the", "services", "solutions", "staffing"}
        and len(p) >= 3
    ]

    for item in organic:
        title = item.get("title", "").lower()
        snippet = item.get("snippet", "").lower()
        link = item.get("link", "")
        combined = title + " " + snippet

        has_recruiter = all(part in combined for part in recruiter_parts)
        has_company = not company_parts or any(cp in combined for cp in company_parts)

        if has_recruiter and has_company:
            return SignalResult(
                signal_key="recruiter_check",
                signal_name="Recruiter Identity Verification",
                engine="google",
                score_delta=-12,
                status="pass",
                finding=f"Public professional profile confirmed: {item.get('title', recruiter)} affiliated with {company}.",
                query_used=query,
                evidence_url=link,
                search_url=search_url,
            )

    return SignalResult(
        signal_key="recruiter_check",
        signal_name="Recruiter Identity Verification",
        engine="google",
        score_delta=10,
        status="fail",
        finding=f"No public professional record or LinkedIn profile connects '{recruiter}' to '{company}'.",
        query_used=query,
        evidence_url=None,
        search_url=search_url,
    )
