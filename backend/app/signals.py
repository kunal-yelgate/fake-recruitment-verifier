"""Parallel SerpApi and text forensic signal evaluators for cross-checking job postings with live web data."""

import asyncio
import urllib.parse
from typing import List, Optional
from app.models import ExtractedFields, SignalResult
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

    data = await serpapi_client.search("google_maps", params)
    local_results = data.get("local_results", [])
    place = data.get("place_results")

    search_url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(query)}"
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

    data = await serpapi_client.search("google", params)
    organic = data.get("organic_results", [])

    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
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

    data = await serpapi_client.search("google", params)
    organic = data.get("organic_results", [])
    count = len(organic)

    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

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

    data = await serpapi_client.search("google_news", params)
    news = data.get("news_results", [])

    search_url = f"https://news.google.com/search?q={urllib.parse.quote_plus(query)}"

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
    company = fields.company_name or ""
    if not company or company == "Undisclosed Company":
        company = "Company"

    query = f'"{company}" official website'
    params = {"q": query}
    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

    # 1. Critical red flag: Recruiter contacts candidate from a free webmail address
    if claimed_domain and claimed_domain in FREE_EMAIL_DOMAINS:
        return SignalResult(
            signal_key="domain_match",
            signal_name="Domain & Email Match",
            engine="google",
            score_delta=25,
            status="fail",
            finding=f"High Risk: Recruiter email uses a free webmail domain (@{claimed_domain}) instead of an official company email domain.",
            query_used=query,
            evidence_url=None,
            search_url=search_url,
        )

    # 2. Check corporate domain via Google search
    data = await serpapi_client.search("google", params)
    organic = data.get("organic_results", [])

    official_domain = ""
    top_link = None
    for item in organic:
        link = item.get("link", "")
        domain = _extract_domain_from_url(link)
        # Exclude directories, social media, job boards, and Wikipedia
        if domain and not any(skip in domain for skip in JOB_PLATFORM_DOMAINS):
            official_domain = domain
            top_link = link
            break

    if not claimed_domain:
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

    # Compare claimed domain vs official domain
    claimed_clean = _extract_domain_from_url(claimed_domain)
    if official_domain and (claimed_clean == official_domain or claimed_clean.endswith("." + official_domain)):
        return SignalResult(
            signal_key="domain_match",
            signal_name="Domain & Email Match",
            engine="google",
            score_delta=-15,
            status="pass",
            finding=f"Claimed domain ({claimed_clean}) directly matches the verified official website ({official_domain}).",
            query_used=query,
            evidence_url=top_link,
            search_url=search_url,
        )

    # Lookalike or domain spoofing detection
    if official_domain and claimed_clean != official_domain:
        # Check if claimed clean shares brand root or has hyphenated lookalike pattern
        brand_stem = official_domain.split(".")[0]
        if brand_stem in claimed_clean or len(claimed_clean.replace("-", "").replace(".", "")) > 3:
            return SignalResult(
                signal_key="domain_match",
                signal_name="Domain & Email Match",
                engine="google",
                score_delta=22,
                status="fail",
                finding=f"Lookalike Domain Alert: Posting references '{claimed_clean}', but official company website is '{official_domain}'.",
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
        finding=f"Domain '{claimed_clean}' could not be definitively cross-referenced with top search results.",
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
    data = await serpapi_client.search("google", params)
    organic = data.get("organic_results", [])

    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

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
    return results
