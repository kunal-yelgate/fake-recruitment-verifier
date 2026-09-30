"""Company physical footprint signal."""

import urllib.parse

from app.models import ExtractedFields, SignalResult
from app.serpapi_client import serpapi_client

from .shared import _unavailable_search_signal


async def check_company_footprint(fields: ExtractedFields) -> SignalResult:
    """Check 2: Google Maps real-world physical presence check."""
    company = fields.company_name or ""
    if not company or company == "Undisclosed Company":
        return SignalResult(
            signal_key="company_footprint",
            signal_name="Company Physical Footprint",
            engine="google_maps",
            score_delta=0,
            status="warning",
            finding="Company name not disclosed in posting; physical footprint check bypassed.",
            query_used="N/A",
            evidence_url=None,
            search_url=None,
        )

    query = company
    params = {"q": query}
    search_url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(query)}"

    data = await serpapi_client.search("google_maps", params)
    unavailable = _unavailable_search_signal(data, "Company Physical Footprint", "google_maps", query, search_url)
    if unavailable:
        unavailable.signal_key = "company_footprint"
        return unavailable
    local_results = data.get("local_results", [])
    place = data.get("place_results")

    evidence_url = None

    match_found = False
    top_place = None
    candidates = []
    if place:
        candidates.append(place)
    if local_results and isinstance(local_results, list):
        candidates.extend(local_results)

    company_clean = "".join(c for c in company.lower() if c.isalnum() or c.isspace())
    stopwords = {
        "inc",
        "llc",
        "corp",
        "corporation",
        "ltd",
        "limited",
        "group",
        "co",
        "the",
        "services",
        "solutions",
        "agency",
        "staffing",
    }
    specific_words = [w for w in company_clean.split() if w not in stopwords and len(w) >= 3]

    for res in candidates:
        res_title = res.get("title", "").lower()
        if specific_words and all(w in res_title for w in specific_words):
            top_place = res
            match_found = True
            break

    if match_found and top_place:
        title = top_place.get("title", company)
        addr = top_place.get("address", "Registered location")
        evidence_url = top_place.get("website") or search_url
        return SignalResult(
            signal_key="company_footprint",
            signal_name="Company Physical Footprint",
            engine="google_maps",
            score_delta=-15,
            status="pass",
            finding=f"Verified business footprint on Google Maps: '{title}' at {addr}.",
            query_used=query,
            evidence_url=evidence_url,
            search_url=search_url,
        )

    return SignalResult(
        signal_key="company_footprint",
        signal_name="Company Physical Footprint",
        engine="google_maps",
        score_delta=10,
        status="warning",
        finding=f"No verified Google Maps listing or registered headquarters address found for '{company}'.",
        query_used=query,
        evidence_url=None,
        search_url=search_url,
    )
