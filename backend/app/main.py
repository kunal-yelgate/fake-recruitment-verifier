"""FastAPI application entrypoint for Fake Recruiter Verifier."""

import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models import CheckRequest, CheckResponse
from app.extraction import extract_fields
from app.groq_analysis import assess_with_groq
from app.claim_pipeline import run_claim_pipeline, write_cited_explanation
from app.signals import find_linkedin_referral_leads
from app.scoring import calculate_risk_score
from app.cache import cache

app = FastAPI(
    title="Fake Recruiter Verifier API",
    description="""
## What this API does

The Fake Recruiter Verifier analyzes a job posting or recruiter message and returns a transparent risk assessment. It uses the text supplied in `raw_text`, extracts useful entities, checks public signals, and combines the findings into a 0-100 risk score.

## Analysis workflow

1. **Extract claims** - identifies externally verifiable company, recruiter, compensation, contact, domain, address, and hiring-platform statements.
2. **Plan searches** - Groq proposes bounded searches for each claim.
3. **Verify and judge evidence** - SerpApi returns public evidence and Groq classifies it as supporting, contradicting, unrelated, or ambiguous. Ambiguous claims can receive at most two follow-up rounds.
4. **Calculate the result** - deterministic rules apply weighted deltas to a base score of 50 and clamp the result to 0-100.
5. **Return evidence** - provides the claim audit, source snippets, citations, verdict, extracted fields, and safety summary.

The API does not make a legal determination or guarantee that a recruiter is safe. A low-risk result means the available public evidence is corroborating; users should still protect personal and financial information.
""",
    version="1.0.0",
)

# Enable CORS for development frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Service status and quick links."""
    return {
        "service": "Fake Recruiter Verifier API",
        "status": "online",
        "docs": "/docs",
        "check_endpoint": "/check",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/cache/stats")
async def cache_stats():
    """Retrieve SQLite query cache statistics."""
    return cache.get_stats()


@app.post("/check", response_model=CheckResponse)
async def check_posting(request: CheckRequest):
    """
    Analyze one user-provided job posting or recruiter message.

    The endpoint extracts entities, checks in-text scam patterns, then runs six
    public-signal checks in parallel: company footprint, LinkedIn presence,
    duplicate posting fingerprint, fraud/news mentions, domain and email
    integrity, and recruiter affiliation. It returns the weighted 0-100 risk
    score, safety verdict, extracted details, individual findings, and evidence
    links used by the analysis.
    """
    start_time = time.time()

    if not request.raw_text or len(request.raw_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Job posting text is too short to evaluate.")

    # Step 1: Structured extraction (Anthropic LLM or regex fallback)
    extracted = await extract_fields(request.raw_text)

    # Step 2: Extract claims, plan bounded searches, judge evidence, and retain an audit trail.
    claim_audit, signals = await run_claim_pipeline(request.raw_text, extracted)

    # Step 3: Compute weighted score and verdict
    risk_score, verdict, verdict_badge, summary = calculate_risk_score(signals)
    claim_audit.explanation = await write_cited_explanation(
        claim_audit.judgments,
        risk_score,
    )

    # Optional Groq second opinion; kept separate from the uncalibrated numeric score.
    groq_decision = await assess_with_groq(request.raw_text, signals)
    linkedin_referral_leads = []
    if groq_decision and groq_decision.recommendation == "apply":
        linkedin_referral_leads = await find_linkedin_referral_leads(extracted)

    # Surface demo mode and provider failures instead of presenting them as live evidence.
    is_mock = (
        not bool(settings.serpapi_key and settings.serpapi_key.strip() not in ("", "your_serpapi_key_here"))
        or any(signal.data_source == "mock" for signal in signals)
    )

    elapsed = round(time.time() - start_time, 3)

    return CheckResponse(
        risk_score=risk_score,
        verdict=verdict,
        verdict_badge=verdict_badge,
        base_score=50,
        extracted_fields=extracted,
        signals=signals,
        claim_audit=claim_audit,
        groq_decision=groq_decision,
        linkedin_referral_leads=linkedin_referral_leads,
        summary=summary,
        is_mock=is_mock,
        execution_time_seconds=elapsed,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
