"""Extraction engine for converting unstructured posting text into structured fields.

Supports Anthropic Claude LLM if ANTHROPIC_API_KEY is present, with an extensive
regex fallback for zero-dependency local operation.
"""

import json
import re
from typing import Optional
from app.config import settings
from app.models import ExtractedFields


def extract_with_regex(raw_text: str) -> ExtractedFields:
    """Robust regex-based fallback extractor for job posting attributes."""
    cleaned = raw_text.strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]

    # 1. Contact Email
    email_match = re.search(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", cleaned
    )
    contact_email = email_match.group(0).lower() if email_match else None

    # 2. Claimed Domain
    claimed_domain: Optional[str] = None
    domain_header_match = re.search(
        r"(?:Domain|Website|Web)\s*[:\-]\s*([a-zA-Z0-9-]+\.[a-zA-Z]{2,})", cleaned, re.IGNORECASE
    )
    if domain_header_match:
        claimed_domain = domain_header_match.group(1).lower()
    elif contact_email:
        domain_part = contact_email.split("@")[-1]
        claimed_domain = domain_part.lower()
    else:
        url_match = re.search(
            r"https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})(?:/[^\s]*)?", cleaned
        )
        if url_match:
            claimed_domain = url_match.group(1).lower()

    # 3. Company Name
    company_name: Optional[str] = None
    company_patterns = [
        r"(?:Company|Employer|Organization|Hiring Company)\s*[:\-]\s*([A-Za-z0-9&.,' ]{2,50})",
        r"(?:About|Welcome to)\s+([A-Z][A-Za-z0-9&.,' ]{2,35})",
        r"(?:join|at|with)\s+([A-Z][A-Za-z0-9&' ]{2,30})\s+(?:as a|team|is hiring)",
        r"^([A-Z][A-Za-z0-9&' ]{2,30})\s+is seeking",
    ]
    for pattern in company_patterns:
        m = re.search(pattern, cleaned, re.MULTILINE | re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            # Filter out generic words
            if candidate.lower() not in ["the", "this company", "our company", "remote team"]:
                company_name = candidate
                break

    # If still not found, check first header line
    if not company_name and lines:
        first_line = lines[0]
        if " - " in first_line:
            parts = first_line.split(" - ")
            company_name = parts[0].strip()
        elif " at " in first_line:
            parts = first_line.split(" at ")
            company_name = parts[-1].strip()

    # Infer company name from domain if email is corporate and company is unknown
    if not company_name and contact_email and claimed_domain:
        free_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "proton.me", "protonmail.com"}
        if claimed_domain not in free_domains:
            name_part = claimed_domain.split(".")[0]
            if len(name_part) >= 3:
                company_name = name_part.capitalize()

    # Default company fallback if undetectable
    if not company_name:
        company_name = "Undisclosed Company"

    # 4. Recruiter Name
    recruiter_name: Optional[str] = None
    recruiter_patterns = [
        r"(?:Recruiter|Hiring Manager|Contact Person|HR Contact|Talent Acquisition|From)\s*[:\-]\s*([A-Z][a-z]+ [A-Z][a-z]+)",
        r"(?:My name is|I am|Reach out to|Contact Mr\.|Contact Ms\.)\s+([A-Z][a-z]+ [A-Z][a-z]+)",
    ]
    for pattern in recruiter_patterns:
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            recruiter_name = m.group(1).strip()
            break

    # 5. Job Title
    job_title: Optional[str] = None
    title_patterns = [
        r"(?:Job Title|Position|Role|Opening)\s*[:\-]\s*([A-Za-z0-9 /&\-]{3,50})",
        r"(?:Hiring for|Looking for a|Seeking a)\s+([A-Za-z0-9 /&\-]{3,40})",
    ]
    for pattern in title_patterns:
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            job_title = m.group(1).strip()
            break

    # 6. Distinctive Phrase (8-12 words from body for fingerprinting)
    distinctive_phrase = _extract_distinctive_phrase(lines)

    return ExtractedFields(
        company_name=company_name,
        recruiter_name=recruiter_name,
        claimed_domain=claimed_domain,
        contact_email=contact_email,
        distinctive_phrase=distinctive_phrase,
        job_title=job_title,
        extraction_method="regex",
    )


def _extract_distinctive_phrase(lines: list[str]) -> str:
    """Find a unique, non-boilerplate sentence suitable for exact-match duplicate detection."""
    boilerplate_words = {"equal opportunity", "benefits", "apply now", "requirements", "qualification", "job title", "salary"}

    for line in lines[1:]:
        clean_line = line.strip()
        words = clean_line.split()
        if 6 <= len(words) <= 20:
            lower = clean_line.lower()
            if not any(bw in lower for bw in boilerplate_words) and not lower.startswith("http"):
                # Clean punctuation for exact phrase search
                return " ".join(words[:10])

    # Fallback to first multi-word line
    for line in lines:
        words = line.strip().split()
        if len(words) >= 6:
            return " ".join(words[:10])

    return "Job opportunity remote position hiring immediately"


async def extract_fields(raw_text: str) -> ExtractedFields:
    """Extract fields using Anthropic LLM if key is configured, else regex fallback."""
    if not settings.anthropic_api_key or settings.anthropic_api_key.strip() in ("", "your_key_here"):
        return extract_with_regex(raw_text)

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        prompt = (
            "You are an expert fraud investigator analyzing a job posting. "
            "Extract structured fields in valid JSON matching this schema:\n"
            "{\n"
            '  "company_name": "Company Name",\n'
            '  "recruiter_name": "Recruiter Name or null",\n'
            '  "claimed_domain": "Domain or null",\n'
            '  "contact_email": "email or null",\n'
            '  "job_title": "Job Title or null",\n'
            '  "distinctive_phrase": "A unique 10-15 word exact sentence from the posting for spam fingerprinting"\n'
            "}\n"
            "Return ONLY the raw JSON object, no explanation."
        )

        message = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=0.0,
            messages=[
                {"role": "user", "content": f"{prompt}\n\nJob Posting:\n{raw_text[:2500]}"}
            ],
        )

        response_text = message.content[0].text.strip()
        data = json.loads(response_text)
        return ExtractedFields(
            company_name=data.get("company_name") or "Undisclosed Company",
            recruiter_name=data.get("recruiter_name"),
            claimed_domain=data.get("claimed_domain"),
            contact_email=data.get("contact_email"),
            distinctive_phrase=data.get("distinctive_phrase"),
            job_title=data.get("job_title"),
            extraction_method="llm",
        )
    except Exception:
        # Gracefully fall back to regex on any API or parsing failure
        return extract_with_regex(raw_text)
