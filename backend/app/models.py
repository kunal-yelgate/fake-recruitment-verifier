"""Pydantic schemas for request, response, and intermediate verification data."""

from typing import List, Literal, Optional
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
    salary_range: Optional[str] = Field(None, description="Salary or compensation range stated in the posting")
    payment_requests: List[str] = Field(
        default_factory=list,
        description="Exact payment, deposit, gift-card, crypto, or fee requests found in the posting",
    )
    extraction_method: str = Field("regex", description="'groq', 'llm' (Anthropic), or 'regex'")


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
    data_source: str = Field(
        default="live",
        description="Evidence source: live search, source text, mock demo data, or unavailable provider response",
    )


class GroqDecision(BaseModel):
    recommendation: Literal[
        "apply",
        "do_not_apply",
        "verify_before_applying",
    ]
    explanation: str = Field(..., min_length=1, max_length=400)
    evidence_quotes: List[str] = Field(..., min_length=1, max_length=4)


class LinkedInReferralLead(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    headline: str = Field(default="", max_length=300)
    profile_url: str = Field(..., min_length=1, max_length=500)
    search_evidence: str = Field(..., min_length=1, max_length=500)


class VerifiableClaim(BaseModel):
    claim_id: str
    claim_type: str
    text: str = Field(..., min_length=1, max_length=300)
    value: str = Field(..., min_length=1, max_length=300)
    source_quote: str = Field(..., min_length=1, max_length=500)
    importance: Literal["high", "medium", "low"] = "medium"


class SearchPlan(BaseModel):
    claim_id: str
    engine: Literal["google", "google_news", "google_maps"]
    query: str = Field(..., min_length=3, max_length=300)
    purpose: str = Field(..., min_length=1, max_length=240)
    round: int = Field(0, ge=0, le=2)


class SearchEvidence(BaseModel):
    claim_id: str
    engine: str
    query: str
    title: str = ""
    snippet: str = ""
    url: Optional[str] = None
    source: Literal["live", "mock", "error", "text"] = "live"


class ClaimJudgment(BaseModel):
    claim_id: str
    classification: Literal["supports", "contradicts", "unrelated", "ambiguous"]
    explanation: str = Field(..., min_length=1, max_length=400)
    source_snippet: str = Field(..., min_length=1, max_length=700)
    evidence_urls: List[str] = Field(default_factory=list, max_length=5)


class FollowUpRequest(BaseModel):
    claim_id: str
    query: str = Field(..., min_length=3, max_length=300)
    engine: Literal["google", "google_news", "google_maps"] = "google"
    reason: str = Field(..., min_length=1, max_length=240)


class CitedExplanation(BaseModel):
    text: str = Field(..., min_length=1, max_length=1600)
    citations: List[str] = Field(default_factory=list, max_length=12)


class ClaimPipelineAudit(BaseModel):
    claims: List[VerifiableClaim] = Field(default_factory=list)
    search_plan: List[SearchPlan] = Field(default_factory=list)
    evidence: List[SearchEvidence] = Field(default_factory=list)
    judgments: List[ClaimJudgment] = Field(default_factory=list)
    follow_ups: List[FollowUpRequest] = Field(default_factory=list)
    explanation: Optional[CitedExplanation] = None
    rounds_completed: int = Field(0, ge=0, le=2)


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
    claim_audit: Optional[ClaimPipelineAudit] = Field(
        None,
        description="Auditable claim extraction, search planning, evidence, judgments, follow-ups, and citations.",
    )
    groq_decision: Optional[GroqDecision] = Field(
        None,
        description="Optional Groq apply recommendation grounded in the posting and live evidence; does not alter risk_score.",
    )
    linkedin_referral_leads: List[LinkedInReferralLead] = Field(
        default_factory=list,
        description="Public LinkedIn search matches for possible company referral contacts; current employment must be verified independently.",
    )
    summary: str = Field(..., description="High-level narrative explaining the risk score")
    is_mock: bool = Field(False, description="True if any search signal used simulated mock data")
    execution_time_seconds: float = Field(..., description="Total processing time in seconds")
