"""Shared constants and helpers for signal evaluators."""

"""Parallel SerpApi and text forensic signal evaluators for cross-checking job postings with live web data."""

import urllib.parse
from datetime import datetime, timezone

import httpx

from app.models import SignalResult

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


def _unavailable_search_signal(
    data: dict, signal_name: str, engine: str, query: str, search_url: str
) -> SignalResult | None:
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
    "ac.uk",
    "co.in",
    "co.jp",
    "co.nz",
    "co.uk",
    "com.au",
    "com.br",
    "com.cn",
    "com.hk",
    "com.mx",
    "com.sg",
    "com.tw",
    "com.ua",
    "com.vn",
    "net.au",
    "org.au",
}
_BRAND_DOMAIN_SUFFIXES = {"careers", "career", "jobs", "job", "hiring", "talent", "recruitment"}
_HOMOGLYPH_TRANSLATION = str.maketrans(
    {
        "0": "o",
        "1": "l",
        "|": "l",
        "3": "e",
        "5": "s",
        "а": "a",
        "ɑ": "a",
        "е": "e",
        "ε": "e",
        "о": "o",
        "ο": "o",
        "р": "p",
        "ρ": "p",
        "с": "c",
        "ϲ": "c",
        "х": "x",
        "χ": "x",
        "у": "y",
        "і": "i",
        "ι": "i",
        "ӏ": "l",
        "к": "k",
        "м": "m",
        "т": "t",
        "в": "b",
        "н": "h",
    }
)


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
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _lookalike_reason(claimed_domain: str, official_domain: str) -> str | None:
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


async def _lookup_domain_age_days(domain: str) -> int | None:
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
            if event.get("eventAction", "").lower() in {"registration", "registered"} and event.get("eventDate")
        )
        registered_at = datetime.fromisoformat(registered.replace("Z", "+00:00"))
        if registered_at.tzinfo is None:
            registered_at = registered_at.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - registered_at).days)
    except Exception:
        return None
