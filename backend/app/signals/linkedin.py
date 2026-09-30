"""LinkedIn corporate presence signal."""

import urllib.parse

from app.models import ExtractedFields, SignalResult
from app.serpapi_client import serpapi_client

from .shared import _unavailable_search_signal


async def check_linkedin_presence(fields: ExtractedFields) -> SignalResult:
    """Check 3: Google search with site:linkedin.com to verify official company page."""
    company = fields.company_name or ""
    if not company or company == "Undisclosed Company":
        return SignalResult(
            signal_key="linkedin_presence",
            signal_name="LinkedIn Corporate Presence",
            engine="google",
            score_delta=0,
            status="warning",
            finding="Company name not disclosed in posting; LinkedIn corporate search bypassed.",
            query_used="N/A",
            evidence_url=None,
            search_url=None,
        )

    query = f'site:linkedin.com/company "{company}"'
    params = {"q": query}
    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

    data = await serpapi_client.search("google", params)
    unavailable = _unavailable_search_signal(data, "LinkedIn Corporate Presence", "google", query, search_url)
    if unavailable:
        unavailable.signal_key = "linkedin_presence"
        return unavailable
    organic = data.get("organic_results", [])

    evidence_url = None

    for item in organic:
        link = item.get("link", "")
        if "linkedin.com/company/" in link:
            evidence_url = link
            return SignalResult(
                signal_key="linkedin_presence",
                signal_name="LinkedIn Corporate Presence",
                engine="google",
                score_delta=-15,
                status="pass",
                finding=f"Active verified LinkedIn corporate page found: {item.get('title', 'Company Profile')}.",
                query_used=query,
                evidence_url=evidence_url,
                search_url=search_url,
            )

    return SignalResult(
        signal_key="linkedin_presence",
        signal_name="LinkedIn Corporate Presence",
        engine="google",
        score_delta=12,
        status="fail",
        finding=f"No corporate LinkedIn page discovered for '{company}'. Legitimate recruiters almost universally maintain an official company presence.",
        query_used=query,
        evidence_url=None,
        search_url=search_url,
    )
