"""FastAPI application entrypoint for Fake Recruiter Verifier."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.cache import cache
from app.claim_pipeline import run_claim_pipeline, write_cited_explanation
from app.config import settings
from app.extraction import extract_fields
from app.groq_analysis import assess_with_groq
from app.metrics import metrics
from app.models import CheckRequest, CheckResponse, FetchURLRequest, FetchURLResponse
from app.observability import configure_logging, elapsed_ms
from app.scoring import calculate_risk_score
from app.signals import find_linkedin_referral_leads
from app.url_fetcher import (
    InvalidURL,
    URLFetchError,
    URLFetchTimeout,
    URLFetchTooLarge,
    URLFetchUnsupportedContent,
    fetch_text,
)

logger = logging.getLogger(__name__)
configure_logging()


def require_authenticated_user(request: Request) -> dict[str, Any]:
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


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Any]]) -> Any:
    """Attach a correlation ID without logging request text or credentials."""
    supplied_id = request.headers.get("x-request-id", "")
    request_id = supplied_id if 1 <= len(supplied_id) <= 128 and supplied_id.isprintable() else uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request failed",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path,
                   "duration_ms": elapsed_ms(started)},
        )
        raise
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request completed",
        extra={"request_id": request_id, "method": request.method, "path": request.url.path,
               "status_code": response.status_code, "duration_ms": elapsed_ms(started)},
    )
    return response


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
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Service status and quick links."""
    return {
        "service": "Fake Recruiter Verifier API",
        "status": "online",
        "docs": "/docs",
        "check_endpoint": "/check",
    }


@app.get("/health")
async def health_check() -> dict[str, float | str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/cache/stats")
async def cache_stats() -> dict[str, Any]:
    """Retrieve SQLite query cache statistics."""
    return cache.get_stats()


@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> str:
    """Expose privacy-safe counters for cache and provider health."""
    return metrics.prometheus()


@app.post("/fetch-url", response_model=FetchURLResponse)
@limiter.limit(f"{settings.rate_limit_per_min}/minute")
async def fetch_job_url(request: Request, payload: FetchURLRequest) -> FetchURLResponse:
    """Fetch bounded text from a public HTTP(S) job posting URL.

    OCR uploads are intentionally not enabled: the project has no vetted OCR
    dependency, and accepting arbitrary image processing without one would
    expand the security boundary.
    """
    require_authenticated_user(request)
    try:
        result = await fetch_text(
            payload.url,
            timeout_seconds=settings.url_fetch_timeout_seconds,
            max_bytes=settings.url_fetch_max_bytes,
            max_redirects=settings.url_fetch_max_redirects,
        )
    except InvalidURL as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except URLFetchTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except URLFetchUnsupportedContent as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except URLFetchTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except URLFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return FetchURLResponse(
        text=result.text,
        final_url=result.final_url,
        content_type=result.content_type,
    )


@app.post("/check", response_model=CheckResponse)
@limiter.limit(f"{settings.rate_limit_per_min}/minute")
async def check_posting(request: Request, payload: CheckRequest) -> CheckResponse:
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

    try:
        # Step 1: Structured extraction (Anthropic LLM or regex fallback)
        extracted = await extract_fields(payload.raw_text)

        # Step 2: Extract claims, plan bounded searches, judge evidence, and retain an audit trail.
        claim_audit, signals = await run_claim_pipeline(payload.raw_text, extracted)
        for signal in signals:
            if signal.status == "pass":
                signal.confidence = "pass"
            elif signal.status == "fail":
                signal.confidence = "fail"
            else:
                signal.confidence = "unknown"

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
    except Exception as exc:
        logger.exception("Verification pipeline failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "verification_unavailable",
                "message": "Verification is temporarily unavailable. Please try again.",
            },
        ) from exc

    # Surface demo mode and provider failures instead of presenting them as live evidence.
    is_mock = not bool(
        settings.serpapi_key and settings.serpapi_key.strip() not in ("", "your_serpapi_key_here")
    ) or any(signal.data_source == "mock" for signal in signals)
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

    if data_quality == "live" and signals and all(signal.confidence != "unknown" for signal in signals):
        overall_confidence = "high"
    elif data_quality in {"live", "partial"}:
        overall_confidence = "medium"
    else:
        overall_confidence = "low"

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
        overall_confidence=overall_confidence,
        execution_time_seconds=elapsed,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
