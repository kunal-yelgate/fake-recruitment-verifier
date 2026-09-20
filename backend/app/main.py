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
    description="Live search verification against SerpApi to corroborate job postings and detect recruitment scams.",
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
    Main verification endpoint.
    1. Extracts structured fields (company, recruiter, domain, distinctive phrase).
    2. Runs 6 parallel live SerpApi search queries (Maps, LinkedIn, Duplicates, News, Domain, Recruiter).
    3. Calculates transparent weighted risk score clamped from 0 to 100.
    4. Returns actionable verdict with clickable evidence links.
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
