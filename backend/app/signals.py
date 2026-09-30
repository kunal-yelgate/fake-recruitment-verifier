"""Parallel SerpApi and text forensic signal evaluators for cross-checking job postings with live web data."""

import asyncio
from datetime import datetime, timezone
import re
import urllib.parse
from typing import List, Optional
import httpx
from app.config import settings
from app.groq_analysis import select_official_domain_with_groq
from app.models import ExtractedFields, LinkedInReferralLead, SignalResult
from app.serpapi_client import serpapi_client

FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "yahoo.co.uk",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "icloud.com",
    "mail.com",
    "zoho.com",
    "gmx.com",
    "yandex.com",
    "tutanota.com",
    "live.com",
    "mail.ru",
    "fastmail.com",
    "hushmail.com",
}


def _unavailable_search_signal(data: dict, signal_name: str, engine: str, query: str, search_url: str) -> Optional[SignalResult]:
    """Return a neutral result when a provider error cannot support evidence."""
    if data.get("_source") != "error":
        return None
    return SignalResult(
        signal_key=signal_name.lower().replace(" ", "_"),
        signal_name=signal_name,
        engine=engine,
        score_delta=0,
        status="warning",
        finding="Verification unavailable because the search provider returned an error. No risk points were applied.",
        query_used=query,
        evidence_url=None,
        search_url=search_url,
        data_source="error",
    )

JOB_PLATFORM_DOMAINS = {
    "indeed.com",
    "glassdoor.com",
    "linkedin.com",
    "monster.com",
    "ziprecruiter.com",
    "lever.co",
    "greenhouse.io",
    "workday.com",
    "workable.com",
    "ashbyhq.com",
    "bamboohr.com",
    "smartrecruiters.com",
    "wikipedia.org",
    "facebook.com",
    "bloomberg.com",
    "crunchbase.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "instagram.com",
    "medium.com",
}


def _extract_domain_from_url(url: str) -> str:
    """Extract clean domain (e.g., example.com) from any URL string."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower().split(":")[0]
    except Exception:
        return ""


_COMPOUND_PUBLIC_SUFFIXES = {
    "ac.uk", "co.in", "co.jp", "co.nz", "co.uk", "com.au", "com.br",
    "com.cn", "com.hk", "com.mx", "com.sg", "com.tw", "com.ua", "com.vn",
    "net.au", "org.au",
}
_BRAND_DOMAIN_SUFFIXES = {"careers", "career", "jobs", "job", "hiring", "talent", "recruitment"}
_HOMOGLYPH_TRANSLATION = str.maketrans({
    "0": "o", "1": "l", "|": "l", "3": "e", "5": "s",
    "а": "a", "ɑ": "a", "е": "e", "ε": "e", "о": "o", "ο": "o",
    "р": "p", "ρ": "p", "с": "c", "ϲ": "c", "х": "x", "χ": "x",
    "у": "y", "і": "i", "ι": "i", "ӏ": "l", "к": "k", "м": "m",
    "т": "t", "в": "b", "н": "h",
})


def _domain_brand_label(domain: str) -> str:
    """Return the likely registrant label for common public suffix formats."""
    host = _extract_domain_from_url(domain).rstrip(".")
    labels = host.split(".")
    if len(labels) < 2:
        return labels[0]
    suffix = ".".join(labels[-2:])
    return labels[-3] if suffix in _COMPOUND_PUBLIC_SUFFIXES and len(labels) >= 3 else labels[-2]


def _registrable_domain(domain: str) -> str:
    """Return the registrable domain so legitimate subdomains compare as one site."""
    host = _extract_domain_from_url(domain).rstrip(".")
    labels = host.split(".")
    if len(labels) < 2:
        return host
    suffix = ".".join(labels[-2:])
    label_count = 3 if suffix in _COMPOUND_PUBLIC_SUFFIXES else 2
    return ".".join(labels[-label_count:])


def _levenshtein_distance(left: str, right: str) -> int:
    """Compute edit distance for short domain labels without another dependency."""
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[right_index] + 1,
                previous[right_index - 1] + (left_char != right_char),
            ))
        previous = current
    return previous[-1]


def _lookalike_reason(claimed_domain: str, official_domain: str) -> Optional[str]:
    """Detect close-spelling, homoglyph, and brand-plus-job-word domain imitations."""
    claimed_host = _extract_domain_from_url(claimed_domain).rstrip(".")
    official_host = _extract_domain_from_url(official_domain).rstrip(".")
    if claimed_host == official_host or claimed_host.endswith("." + official_host):
        return None

    claimed_label = _domain_brand_label(claimed_host)
    official_label = _domain_brand_label(official_host)
    claimed_skeleton = claimed_label.translate(_HOMOGLYPH_TRANSLATION)
    official_skeleton = official_label.translate(_HOMOGLYPH_TRANSLATION)

    if claimed_skeleton == official_skeleton:
        return "uses characters that resemble the official company domain"
    if claimed_label.startswith("xn--"):
        return "uses an internationalized domain label that may visually imitate the official domain"

    words = claimed_label.split("-")
    while words and words[-1] in _BRAND_DOMAIN_SUFFIXES:
        words.pop()
    if "".join(words) == official_label.replace("-", ""):
        return "adds job or recruiting words to the company name in a different domain"

    distance = _levenshtein_distance(claimed_skeleton, official_skeleton)
    longest = max(len(claimed_skeleton), len(official_skeleton))
    similarity = 1 - distance / longest if longest else 1
    if distance <= 1 and longest >= 5 or distance <= 2 and longest >= 9 and similarity >= 0.82:
        return f"has a spelling only {distance} character change(s) from the official domain"
    return None


async def _lookup_domain_age_days(domain: str) -> Optional[int]:
    """Look up registration age through public RDAP; unavailable data is ignored."""
    host = _extract_domain_from_url(domain).rstrip(".")
    if not host or host.startswith("xn--") or host in FREE_EMAIL_DOMAINS:
        return None
    try:
        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
            response = await client.get(f"https://rdap.org/domain/{urllib.parse.quote(host, safe='')}")
            response.raise_for_status()
            payload = response.json()
        registered = next(
            event.get("eventDate")
            for event in payload.get("events", [])
            if event.get("eventAction", "").lower() in {"registration", "registered"}
            and event.get("eventDate")
        )
        registered_at = datetime.fromisoformat(registered.replace("Z", "+00:00"))
        if registered_at.tzinfo is None:
            registered_at = registered_at.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - registered_at).days)
    except Exception:
        return None


async def check_in_text_threats(fields: ExtractedFields, raw_text: str = "") -> SignalResult:
    """Check 1: Internal NLP & Regex scanner for explicit in-posting fraud patterns."""
    text_lower = raw_text.lower()
    threats_found = []

    # Check 1: Check Deposit / Upfront Hardware Fraud
    check_deposit_keywords = [
        "check deposit", "deposit check", "cashier check", "upfront check",
        "purchase equipment", "purchase hardware", "buy hardware", "buy equipment",
        "wire transfer", "western union", "moneygram"
    ]
    matched_checks = [kw for kw in check_deposit_keywords if kw in text_lower]
    if matched_checks:
        threats_found.append(f"Check deposit / equipment purchase trap detected ('{matched_checks[0]}')")

    # Check 2: Unverified Instant Messaging Redirects for Interviewing
    chat_redirect_keywords = [
        "telegram", "@hr", "@recruiter", "wa.me", "whatsapp", "signal app",
        "google chat", "hangouts"
    ]
    matched_chats = [kw for kw in chat_redirect_keywords if kw in text_lower]
    if matched_chats:
        threats_found.append(f"Unverified chat interview redirect ('{matched_chats[0]}')")

    # Check 3: Non-standard Payouts / Crypto
    crypto_keywords = ["bitcoin", "usdt", "crypto", "gift card"]
    matched_crypto = [kw for kw in crypto_keywords if kw in text_lower]
    if matched_crypto:
        threats_found.append(f"Non-standard cryptocurrency / gift card payment request ('{matched_crypto[0]}')")

    # Check 4: Unrealistic Pay-for-Effort Ratio
    if any(title in text_lower for title in ["data entry", "administrative assistant", "clerk", "typist"]):
        if any(rate in text_lower for rate in ["$40", "$45", "$50", "$55", "$60", "$70"]) and ("no experience" in text_lower or "immediate" in text_lower):
            threats_found.append("Unrealistic pay rate ($40+/hr) for low-skill entry position")

    if len(threats_found) >= 2 or any("check deposit" in t.lower() or "chat interview" in t.lower() for t in threats_found):
        reasons = "; ".join(threats_found)
        return SignalResult(
            signal_key="text_threat_signals",
            signal_name="In-Posting Threat Patterns",
            engine="nlp_regex",
            score_delta=25,
            status="fail",
            finding=f"Critical Fraud Alert: Posting contains explicit scam signatures: {reasons}.",
            query_used="In-text NLP Threat Pattern Scan",
            evidence_url=None,
            search_url=None,
            data_source="text",
        )
    elif len(threats_found) == 1:
        return SignalResult(
            signal_key="text_threat_signals",
            signal_name="In-Posting Threat Patterns",
            engine="nlp_regex",
            score_delta=10,
            status="warning",
            finding=f"Caution: Posting contains potential threat pattern: {threats_found[0]}.",
            query_used="In-text NLP Threat Pattern Scan",
            evidence_url=None,
            search_url=None,
            data_source="text",
        )

    return SignalResult(
        signal_key="text_threat_signals",
        signal_name="In-Posting Threat Patterns",
        engine="nlp_regex",
        score_delta=-10,
        status="pass",
        finding="No in-text scam signatures, check deposit traps, or unverified chat redirects detected.",
        query_used="In-text NLP Threat Pattern Scan",
        evidence_url=None,
        search_url=None,
        data_source="text",
    )


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
    stopwords = {"inc", "llc", "corp", "corporation", "ltd", "limited", "group", "co", "the", "services", "solutions", "agency", "staffing"}
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


async def check_news_fraud(fields: ExtractedFields) -> SignalResult:
    """Check 5: Google News scan for scam, fraud, or lawsuit complaints with false-positive protection."""
    company = fields.company_name or ""
    if not company or company == "Undisclosed Company":
        return SignalResult(
            signal_key="news_fraud_mentions",
            signal_name="News Fraud & Scam Mentions",
            engine="google_news",
            score_delta=0,
            status="pass",
            finding="Company name not disclosed; news fraud check bypassed.",
            query_used="N/A",
            evidence_url=None,
            search_url=None,
        )

    query = f'"{company}" (scam OR fraud OR fake OR lawsuit OR complaint)'
    params = {"q": query}
    search_url = f"https://news.google.com/search?q={urllib.parse.quote_plus(query)}"

    data = await serpapi_client.search("google_news", params)
    unavailable = _unavailable_search_signal(data, "News Fraud & Scam Mentions", "google_news", query, search_url)
    if unavailable:
        unavailable.signal_key = "news_fraud_mentions"
        return unavailable
    news = data.get("news_results", [])

    if news and len(news) > 0:
        top_news = news[0]
        headline = top_news.get("title", "Fraud report")
        snippet = top_news.get("snippet", "")
        source = top_news.get("source", "News Alert")
        link = top_news.get("link") or search_url

        combined_text = (headline + " " + snippet).lower()

        # False positive check: Is the news about scams IMPERSONATING the company?
        impersonation_markers = [
            "warns", "warning", "targets", "impersonating", "impostor",
            "fake jobs impersonate", "protect against", "scam alert targeting",
            "beware of fake", "identity theft impersonating"
        ]
        if any(marker in combined_text for marker in impersonation_markers):
            return SignalResult(
                signal_key="news_fraud_mentions",
                signal_name="News Fraud & Scam Mentions",
                engine="google_news",
                score_delta=-5,
                status="pass",
                finding=f"Media alerts describe fake scams impersonating '{company}', but no direct fraud complaints against the official entity.",
                query_used=query,
                evidence_url=link,
                search_url=search_url,
            )

        return SignalResult(
            signal_key="news_fraud_mentions",
            signal_name="News Fraud & Scam Mentions",
            engine="google_news",
            score_delta=20,
            status="fail",
            finding=f"Public fraud complaints or scam alerts detected: \"{headline}\" ({source}).",
            query_used=query,
            evidence_url=link,
            search_url=search_url,
        )

    return SignalResult(
        signal_key="news_fraud_mentions",
        signal_name="News Fraud & Scam Mentions",
        engine="google_news",
        score_delta=-5,
        status="pass",
        finding=f"No negative press, regulatory enforcement, or scam complaints discovered in Google News for '{company}'.",
        query_used=query,
        evidence_url=None,
        search_url=search_url,
    )


async def check_domain_match(fields: ExtractedFields) -> SignalResult:
    """Check 6: Lookalike domain & recruiter email verification."""
    claimed_domain = fields.claimed_domain
    email_domain = fields.contact_email.rsplit("@", 1)[-1].lower() if fields.contact_email and "@" in fields.contact_email else None
    free_email_domain = email_domain if email_domain in FREE_EMAIL_DOMAINS else (
        claimed_domain if claimed_domain and claimed_domain.lower() in FREE_EMAIL_DOMAINS else None
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
            return SignalResult(
                signal_key="domain_match",
                signal_name="Domain & Email Match",
                engine="google",
                score_delta=25,
                status="fail",
                finding=f"Recruiter contact uses free email ({free_email_domain}); the official company-domain search was unavailable.",
                query_used=query,
                evidence_url=None,
                search_url=search_url,
                data_source="text",
            )
        unavailable.signal_key = "domain_match"
        return unavailable
    organic = data.get("organic_results", [])

    candidate_domains = []
    for item in organic:
        link = item.get("link", "")
        domain = _extract_domain_from_url(link)
        # Exclude directories, social media, job boards, and Wikipedia
        if domain and not any(skip in domain for skip in JOB_PLATFORM_DOMAINS):
            candidate_domains.append({
                "candidate_index": len(candidate_domains),
                "domain": domain,
                "link": link,
                "title": item.get("title", "")[:300],
                "snippet": item.get("snippet", "")[:500],
            })

    official_domain = ""
    top_link = None
    groq_evidence = None
    if data.get("_source") == "live" and candidate_domains:
        selection = await select_official_domain_with_groq(company, candidate_domains)
        if selection:
            official_domain, groq_evidence = selection
            selected_candidate = next(
                candidate for candidate in candidate_domains
                if _extract_domain_from_url(candidate["link"]) == official_domain
            )
            top_link = selected_candidate["link"]

    if not official_domain and candidate_domains:
        official_domain = candidate_domains[0]["domain"]
        top_link = candidate_domains[0]["link"]

    groq_note = f" Groq selected this live result based on: \"{groq_evidence}\"." if groq_evidence else ""

    claimed_clean = _extract_domain_from_url(claimed_domain) if claimed_domain else ""
    if claimed_clean in FREE_EMAIL_DOMAINS:
        claimed_clean = ""

    domain_age = await _lookup_domain_age_days(claimed_clean) if claimed_clean else None
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
            finding=f"Recruiter contact uses free email ({free_email_domain}) rather than a company address.{official_note}{groq_note}{age_note}",
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

    if official_domain and (
        _registrable_domain(claimed_clean) == _registrable_domain(official_domain)
    ):
        return SignalResult(
            signal_key="domain_match",
            signal_name="Domain & Email Match",
            engine="google",
            score_delta=-15,
            status="pass",
            finding=f"Claimed domain ({claimed_clean}) belongs to the same registered domain as the apparent official website ({official_domain}).{groq_note}{age_note}",
            query_used=query,
            evidence_url=top_link,
            search_url=search_url,
        )

    if official_domain and claimed_clean != official_domain:
        is_job_platform = any(
            claimed_clean == platform or claimed_clean.endswith("." + platform)
            for platform in JOB_PLATFORM_DOMAINS
        )
        lookalike_reason = None if is_job_platform else _lookalike_reason(claimed_clean, official_domain)
        if lookalike_reason:
            return SignalResult(
                signal_key="domain_match",
                signal_name="Domain & Email Match",
                engine="google",
                score_delta=22,
                status="fail",
                finding=f"Lookalike domain alert: '{claimed_clean}' {lookalike_reason}; apparent official site is '{official_domain}'.{groq_note}{age_note}",
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
            finding=f"Could not confirm that '{claimed_clean}' belongs to '{company}'.{age_note}",
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
            f"Apparent official site: {official_domain or 'not found'}.{groq_note}{age_note}"
        ),
        query_used=query,
        evidence_url=top_link,
        search_url=search_url,
    )


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
    company_parts = [p for p in company_clean.split() if p not in {"inc", "llc", "corp", "ltd", "group", "co", "the", "services", "solutions", "staffing"} and len(p) >= 3]

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


async def find_linkedin_referral_leads(fields: ExtractedFields) -> List[LinkedInReferralLead]:
    """Return public LinkedIn profile search matches tied to the named employer."""
    company = fields.company_name or ""
    if not company or company == "Undisclosed Company":
        return []

    query = (
        f'site:linkedin.com/in "{company}" '
        '(recruiter OR "talent acquisition" OR "hiring manager" OR engineer)'
    )
    data = await serpapi_client.search("google", {"q": query})
    if data.get("_source") != "live":
        return []

    stopwords = {"inc", "llc", "corp", "corporation", "ltd", "limited", "group", "co", "the", "company", "services", "solutions", "agency", "staffing"}
    company_tokens = {
        part for part in re.findall(r"[a-z0-9]+", company.casefold())
        if len(part) >= 3 and part not in stopwords
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
        leads.append(LinkedInReferralLead(
            name=name[:160],
            headline=snippet[:300],
            profile_url=profile_url,
            search_evidence=evidence[:500],
        ))
        if len(leads) == 5:
            break

    return leads


async def evaluate_all_signals(fields: ExtractedFields, raw_text: str = "") -> List[SignalResult]:
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
    results: List[SignalResult] = await asyncio.gather(*tasks)
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
