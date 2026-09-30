"""FastAPI application entrypoint for Fake Recruiter Verifier."""

import time
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.config import settings
from app.models import CheckRequest, CheckResponse
from app.extraction import extract_fields
from app.groq_analysis import assess_with_groq
from app.claim_pipeline import run_claim_pipeline, write_cited_explanation
from app.signals import find_linkedin_referral_leads
from app.scoring import calculate_risk_score
from app.cache import cache


def require_authenticated_user(request: Request) -> dict:
    """Validate a Clerk session JWT and fail closed when auth is not configured."""
    if not settings.require_auth:
        return {"sub": "test-user"}

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.casefold() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Sign in is required to run a scan.")
    if not settings.clerk_jwt_key:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured on this server.",
        )

    decode_kwargs = {
        "algorithms": ["RS256"],
        "options": {"verify_aud": False},
    }
    if settings.clerk_issuer:
        decode_kwargs["issuer"] = settings.clerk_issuer
    try:
        return jwt.decode(token, settings.clerk_jwt_key, **decode_kwargs)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired sign-in session.") from exc

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
limiter = Limiter(key_func=get_remote_address, default_limits=[])
app.state.limiter = limiter


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a client-readable limit response with a one-minute retry hint."""
    response = JSONResponse(
        {"error": f"Rate limit exceeded: {exc.detail}"},
        status_code=429,
    )
    response.headers["Retry-After"] = "60"
    return response


app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

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
@limiter.limit(f"{settings.rate_limit_per_min}/minute")
async def check_posting(request: Request, payload: CheckRequest):
    """
    Analyze one user-provided job posting or recruiter message.

    The endpoint extracts entities, checks in-text scam patterns, then runs six
    public-signal checks in parallel: company footprint, LinkedIn presence,
    duplicate posting fingerprint, fraud/news mentions, domain and email
    integrity, and recruiter affiliation. It returns the weighted 0-100 risk
    score, safety verdict, extracted details, individual findings, and evidence
    links used by the analysis.
    """
    require_authenticated_user(request)
    start_time = time.time()

    if not payload.raw_text or len(payload.raw_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Job posting text is too short to evaluate.")

    # Step 1: Structured extraction (Anthropic LLM or regex fallback)
    extracted = await extract_fields(payload.raw_text)

    # Step 2: Extract claims, plan bounded searches, judge evidence, and retain an audit trail.
    claim_audit, signals = await run_claim_pipeline(payload.raw_text, extracted)

    # Step 3: Compute weighted score and verdict
    risk_score, verdict, verdict_badge, summary = calculate_risk_score(signals)
    claim_audit.explanation = await write_cited_explanation(
        claim_audit.judgments,
        risk_score,
    )

    # Optional Groq second opinion; kept separate from the uncalibrated numeric score.
    groq_decision = await assess_with_groq(payload.raw_text, signals)
    linkedin_referral_leads = []
    if groq_decision and groq_decision.recommendation == "apply":
        linkedin_referral_leads = await find_linkedin_referral_leads(extracted)

    # Surface demo mode and provider failures instead of presenting them as live evidence.
    is_mock = (
        not bool(settings.serpapi_key and settings.serpapi_key.strip() not in ("", "your_serpapi_key_here"))
        or any(signal.data_source == "mock" for signal in signals)
    )
    is_demo_only = is_mock or any(signal.data_source == "error" for signal in signals)
    sources = {signal.data_source for signal in signals}
    if sources == {"live"}:
        data_quality = "live"
    elif "live" in sources:
        data_quality = "partial"
    else:
        data_quality = "demo"
    if is_demo_only:
        verdict = "Unverified"
        verdict_badge = "warning"
        summary = (
            "Live verification was not completed. This demo/unavailable result is "
            "not an authoritative scam or legitimacy verdict. "
            f"{summary}"
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
        score_is_authoritative=not is_demo_only,
        is_demo_only=is_demo_only,
        data_quality=data_quality,
        execution_time_seconds=elapsed,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
