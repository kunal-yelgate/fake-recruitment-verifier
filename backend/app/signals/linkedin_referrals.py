"""LinkedIn referral lead lookup."""

import re
import urllib.parse

from app.models import ExtractedFields, LinkedInReferralLead
from app.serpapi_client import serpapi_client


async def find_linkedin_referral_leads(fields: ExtractedFields) -> list[LinkedInReferralLead]:
    """Return public LinkedIn profile search matches tied to the named employer."""
    company = fields.company_name or ""
    if not company or company == "Undisclosed Company":
        return []

    query = f'site:linkedin.com/in "{company}" (recruiter OR "talent acquisition" OR "hiring manager" OR engineer)'
    data = await serpapi_client.search("google", {"q": query})
    if data.get("_source") != "live":
        return []

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
        "company",
        "services",
        "solutions",
        "agency",
        "staffing",
    }
    company_tokens = {
        part for part in re.findall(r"[a-z0-9]+", company.casefold()) if len(part) >= 3 and part not in stopwords
    }
    if not company_tokens:
        return []

    leads = []
    seen_urls = set()
    for item in data.get("organic_results", []):
        link = item.get("link", "")
        parsed = urllib.parse.urlparse(link if "://" in link else f"https://{link}")
        hostname = (parsed.hostname or "").lower()
        if hostname != "linkedin.com" and not hostname.endswith(".linkedin.com"):
            continue
        if not parsed.path.lower().startswith("/in/"):
            continue

        title = item.get("title", "").strip()
        snippet = item.get("snippet", "").strip()
        evidence = f"{title} {snippet}".strip()
        evidence_tokens = set(re.findall(r"[a-z0-9]+", evidence.casefold()))
        if not company_tokens.issubset(evidence_tokens):
            continue

        profile_url = f"https://www.linkedin.com{parsed.path.rstrip('/')}"
        if profile_url in seen_urls:
            continue
        seen_urls.add(profile_url)
        name = title.split("|", 1)[0].strip() or "LinkedIn profile"
        leads.append(
            LinkedInReferralLead(
                name=name[:160],
                headline=snippet[:300],
                profile_url=profile_url,
                search_evidence=evidence[:500],
            )
        )
        if len(leads) == 5:
            break

    return leads
