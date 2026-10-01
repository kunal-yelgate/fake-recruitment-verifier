"""Domain, email, and lookalike-domain signal."""

import asyncio
import urllib.parse
from typing import Any

from app.models import ExtractedFields, SignalResult
from app.serpapi_client import serpapi_client

from .shared import (
    FREE_EMAIL_DOMAINS,
    JOB_PLATFORM_DOMAINS,
    _extract_domain_from_url,
    _lookalike_reason,
    _lookup_domain_age_days,
    _registrable_domain,
    _unavailable_search_signal,
)

try:  # dnspython is optional; DNS failures must never make a check fail.
    import dns.resolver
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    dns = None


def _resolve_txt(name: str) -> list[str]:
    """Resolve TXT records when dnspython is installed, otherwise return unknown."""
    if dns is None:
        return []
    try:
        answers = dns.resolver.resolve(name, "TXT", lifetime=2)
        return [
            b"".join(part if isinstance(part, bytes) else part.encode() for part in answer.strings).decode(
                "utf-8", "replace"
            )
            for answer in answers
        ]
    except Exception:
        return []


def _resolve_mx(name: str) -> bool:
    if dns is None:
        return False
    try:
        return bool(dns.resolver.resolve(name, "MX", lifetime=2))
    except Exception:
        return False


async def _email_auth_hints(domain: str) -> str:
    """Return non-authoritative MX/SPF/DMARC hints without changing risk scoring."""
    if not domain or dns is None:
        return ""
    mx, root_txt, dmarc_txt = await asyncio.gather(
        asyncio.to_thread(_resolve_mx, domain),
        asyncio.to_thread(_resolve_txt, domain),
        asyncio.to_thread(_resolve_txt, f"_dmarc.{domain}"),
    )
    spf = any(record.lower().startswith("v=spf1") for record in root_txt)
    dmarc = any(record.lower().startswith("v=dmarc1") for record in dmarc_txt)
    return f" Email authentication hints: MX={'present' if mx else 'not found'}, SPF={'present' if spf else 'not found'}, DMARC={'present' if dmarc else 'not found'}."


async def check_domain_match(fields: ExtractedFields) -> SignalResult:
    """Check 6: Lookalike domain & recruiter email verification."""
    claimed_domain = fields.claimed_domain
    email_domain = (
        fields.contact_email.rsplit("@", 1)[-1].lower()
        if fields.contact_email and "@" in fields.contact_email
        else None
    )
    free_email_domain = (
        email_domain
        if email_domain in FREE_EMAIL_DOMAINS
        else (claimed_domain if claimed_domain and claimed_domain.lower() in FREE_EMAIL_DOMAINS else None)
    )
    company = fields.company_name or ""
    if not company or company == "Undisclosed Company":
        company = "Company"

    query = f'"{company}" official website'
    params = {"q": query}
    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

    # Search for the company's official site even if the contact email is free webmail.
    data = await serpapi_client.search("google", params)
    unavailable = _unavailable_search_signal(data, "Domain & Email Match", "google", query, search_url)
    if unavailable:
        if free_email_domain:
            auth_note = await _email_auth_hints(email_domain or claimed_domain or "")
            return SignalResult(
                signal_key="domain_match",
                signal_name="Domain & Email Match",
                engine="google",
                score_delta=25,
                status="fail",
                finding=f"Recruiter contact uses free email ({free_email_domain}); the official company-domain search was unavailable.{auth_note}",
                query_used=query,
                evidence_url=None,
                search_url=search_url,
                data_source="text",
            )
        unavailable.signal_key = "domain_match"
        return unavailable
    organic = data.get("organic_results", [])

    candidate_domains: list[dict[str, Any]] = []
    for item in organic:
        link = item.get("link", "")
        domain = _extract_domain_from_url(link)
        # Exclude directories, social media, job boards, and Wikipedia
        if domain and not any(skip in domain for skip in JOB_PLATFORM_DOMAINS):
            candidate_domains.append(
                {
                    "candidate_index": len(candidate_domains),
                    "domain": domain,
                    "link": link,
                    "title": item.get("title", "")[:300],
                    "snippet": item.get("snippet", "")[:500],
                }
            )

    official_domain = ""
    top_link = None
    groq_evidence = None
    if data.get("_source") == "live" and candidate_domains:
        # Resolve through the compatibility facade so existing monkeypatches of
        # ``app.signals.select_official_domain_with_groq`` remain effective.
        from app import signals as signals_facade

        selection = await signals_facade.select_official_domain_with_groq(company, candidate_domains)
        if selection:
            official_domain, groq_evidence = selection
            selected_candidate = next(
                candidate
                for candidate in candidate_domains
                if _extract_domain_from_url(candidate["link"]) == official_domain
            )
            top_link = selected_candidate["link"]

    if not official_domain and candidate_domains:
        official_domain = candidate_domains[0]["domain"]
        top_link = candidate_domains[0]["link"]

    groq_note = f' Groq selected this live result based on: "{groq_evidence}".' if groq_evidence else ""

    claimed_clean = _extract_domain_from_url(claimed_domain) if claimed_domain else ""
    if claimed_clean in FREE_EMAIL_DOMAINS:
        claimed_clean = ""

    domain_age = await _lookup_domain_age_days(claimed_clean) if claimed_clean else None
    auth_note = await _email_auth_hints(email_domain or claimed_clean)
    age_note = (
        f" RDAP reports this domain was registered {domain_age} days ago; young domains deserve extra review."
        if domain_age is not None and domain_age < 90
        else f" RDAP reports this domain is {domain_age} days old."
        if domain_age is not None
        else ""
    )

    if free_email_domain:
        official_note = (
            f" The company's apparent official site is {official_domain}."
            if official_domain
            else " An official company site was not confirmed by search."
        )
        return SignalResult(
            signal_key="domain_match",
            signal_name="Domain & Email Match",
            engine="google",
            score_delta=25,
            status="fail",
            finding=f"Recruiter contact uses free email ({free_email_domain}) rather than a company address.{official_note}{groq_note}{age_note}{auth_note}",
            query_used=query,
            evidence_url=top_link,
            search_url=search_url,
            data_source="text",
        )

    if not claimed_clean:
        return SignalResult(
            signal_key="domain_match",
            signal_name="Domain & Email Match",
            engine="google",
            score_delta=5,
            status="warning",
            finding="No company domain or email address was present in the posting to verify against official web records.",
            query_used=query,
            evidence_url=top_link,
            search_url=search_url,
        )

    if official_domain and (_registrable_domain(claimed_clean) == _registrable_domain(official_domain)):
        return SignalResult(
            signal_key="domain_match",
            signal_name="Domain & Email Match",
            engine="google",
            score_delta=-15,
            status="pass",
            finding=f"Claimed domain ({claimed_clean}) belongs to the same registered domain as the apparent official website ({official_domain}).{groq_note}{age_note}{auth_note}",
            query_used=query,
            evidence_url=top_link,
            search_url=search_url,
        )

    if official_domain and claimed_clean != official_domain:
        is_job_platform = any(
            claimed_clean == platform or claimed_clean.endswith("." + platform) for platform in JOB_PLATFORM_DOMAINS
        )
        lookalike_reason = None if is_job_platform else _lookalike_reason(claimed_clean, official_domain)
        if lookalike_reason:
            return SignalResult(
                signal_key="domain_match",
                signal_name="Domain & Email Match",
                engine="google",
                score_delta=22,
                status="fail",
                finding=f"Lookalike domain alert: '{claimed_clean}' {lookalike_reason}; apparent official site is '{official_domain}'.{groq_note}{age_note}{auth_note}",
                query_used=query,
                evidence_url=top_link,
                search_url=search_url,
            )

    if age_note:
        return SignalResult(
            signal_key="domain_match",
            signal_name="Domain & Email Match",
            engine="google",
            score_delta=0,
            status="warning",
            finding=f"Could not confirm that '{claimed_clean}' belongs to '{company}'.{age_note}{auth_note}",
            query_used=query,
            evidence_url=top_link,
            search_url=search_url,
        )

    return SignalResult(
        signal_key="domain_match",
        signal_name="Domain & Email Match",
        engine="google",
        score_delta=0,
        status="warning",
        finding=(
            f"Domain '{claimed_clean}' could not be definitively cross-referenced with search results. "
            f"Apparent official site: {official_domain or 'not found'}.{groq_note}{age_note}{auth_note}"
        ),
        query_used=query,
        evidence_url=top_link,
        search_url=search_url,
    )
