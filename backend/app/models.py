"""Pydantic schemas for request, response, and intermediate verification data."""

from typing import List, Optional
from pydantic import BaseModel, Field


class CheckRequest(BaseModel):
    """Input payload containing raw job posting text."""
    raw_text: str = Field(
        ...,
        min_length=10,
        description="Raw text of the job posting or recruiter message to analyze.",
    )


class ExtractedFields(BaseModel):
    """Structured fields extracted from the raw posting text."""
    company_name: Optional[str] = Field(None, description="Extracted employer or company name")
    recruiter_name: Optional[str] = Field(None, description="Extracted recruiter or hiring manager name")
    claimed_domain: Optional[str] = Field(None, description="Extracted domain or contact website/email domain")
    contact_email: Optional[str] = Field(None, description="Extracted recruiter email address")
    distinctive_phrase: Optional[str] = Field(None, description="Unique sentence used for duplicate fingerprinting")
    job_title: Optional[str] = Field(None, description="Target job title or role")
    extraction_method: str = Field("regex", description="'llm' (Anthropic) or 'regex'")


class SignalResult(BaseModel):
    """Result of an individual live SerpApi signal check."""
    signal_key: str = Field(..., description="Machine identifier for the signal")
    signal_name: str = Field(..., description="Human-readable title of the check")
    engine: str = Field(..., description="SerpApi engine used (google_maps, google, google_news)")
    score_delta: int = Field(..., description="Points added or subtracted from base score")
    status: str = Field(..., description="'pass' (legit signal), 'warning', 'fail' (scam signal)")
    finding: str = Field(..., description="Summary of evidence found in search results")
    query_used: str = Field(..., description="Exact query string sent to SerpApi")
    evidence_url: Optional[str] = Field(None, description="Direct URL to corroborating evidence or SerpApi link")
    search_url: Optional[str] = Field(None, description="Clickable Google/Maps/News search link for manual review")


class CheckResponse(BaseModel):
    """Complete response returned by POST /check."""
    risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Heuristic risk score from 0 (lower risk signals) to 100 (higher risk signals); not a fraud probability.",
    )
    verdict: str = Field(..., description="'Likely Scam', 'Caution', or 'Likely Legitimate'")
    verdict_badge: str = Field(..., description="'danger', 'warning', or 'success'")
    base_score: int = Field(50, description="Starting neutral baseline score")
    extracted_fields: ExtractedFields
    signals: List[SignalResult]
    summary: str = Field(..., description="High-level narrative explaining the risk score")
    is_mock: bool = Field(False, description="True if mock data was used (no SERPAPI_KEY configured)")
    execution_time_seconds: float = Field(..., description="Total processing time in seconds")
