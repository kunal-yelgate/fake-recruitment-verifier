"""FastAPI application entrypoint for Fake Recruiter Verifier."""

import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models import CheckRequest, CheckResponse
from app.extraction import extract_fields
from app.signals import evaluate_all_signals
from app.scoring import calculate_risk_score
from app.cache import cache

app = FastAPI(
    title="Fake Recruiter Verifier API",
    description="""
## What this API does

The Fake Recruiter Verifier analyzes a job posting or recruiter message and returns a transparent risk assessment. It uses the text supplied in `raw_text`, extracts useful entities, checks public signals, and combines the findings into a 0-100 risk score.

## Analysis workflow

1. **Extract details** - identifies the company, recruiter, email/domain, job title, and distinctive phrases.
2. **Scan the message** - checks for payment requests, check-deposit traps, crypto or gift-card requests, suspicious chat redirects, and unrealistic compensation.
3. **Verify public signals** - runs six concurrent checks for company footprint, LinkedIn presence, duplicate postings, fraud/news mentions, domain/email integrity, and recruiter affiliation.
4. **Calculate the result** - applies transparent weighted signal deltas to a base score of 50 and clamps the result to 0-100.
5. **Return evidence** - provides the verdict, extracted fields, signal findings, search URLs, and a safety summary.

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

    # Step 2: Concurrently evaluate all SerpApi & in-text signals
    signals = await evaluate_all_signals(extracted, request.raw_text)

    # Step 3: Compute weighted score and verdict
    risk_score, verdict, verdict_badge, summary = calculate_risk_score(signals)

    # Check if any signal ran in mock mode (when SERPAPI_KEY is not set)
    is_mock = not bool(settings.serpapi_key and settings.serpapi_key.strip() not in ("", "your_serpapi_key_here"))

    elapsed = round(time.time() - start_time, 3)

    return CheckResponse(
        risk_score=risk_score,
        verdict=verdict,
        verdict_badge=verdict_badge,
        base_score=50,
        extracted_fields=extracted,
        signals=signals,
        summary=summary,
        is_mock=is_mock,
        execution_time_seconds=elapsed,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
