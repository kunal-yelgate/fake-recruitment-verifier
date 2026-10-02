# Fake Recruitment Verifier - Backend Service

FastAPI-powered asynchronous verification service backed by SerpApi live search intelligence and SQLite caching.

## Quick Start

```bash
# 1. Install runtime dependencies
pip install --require-hashes -r requirements.lock

# Optional: enable Anthropic extraction support
pip install -r requirements-optional.txt

# 2. Run the development server
python run.py
# Or with uvicorn directly:
uvicorn app.main:app --reload --port 8000
```

## API Documentation

- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc UI: `http://127.0.0.1:8000/redoc`
- Prometheus metrics: `http://127.0.0.1:8000/metrics`

## Observability

Application logs are one-line JSON records containing the timestamp, level,
event message, route, status, duration, and correlation request ID. Request
bodies, authorization headers, API keys, and query text are never logged.
Clients may send an `X-Request-ID` header (up to 128 printable characters);
otherwise the API generates one and returns it on every response.

`/metrics` exposes privacy-safe Prometheus counters and gauges:

- `truerecruit_cache_hits_total`, `truerecruit_cache_misses_total`, and
  `truerecruit_cache_hit_rate`
- `truerecruit_serpapi_quota_used_total`, counting outbound SerpApi attempts
  (cache hits and demo-mode searches do not consume this counter)
- `truerecruit_serpapi_quota_limit` and
  `truerecruit_serpapi_quota_remaining` when `SERPAPI_QUOTA_LIMIT` is set
- `truerecruit_serpapi_requests_total` and
  `truerecruit_serpapi_errors_total`

Set `SERPAPI_QUOTA_LIMIT` to the provider quota for an optional remaining-quota
gauge; no secret or provider response payload is exposed.

## How the project works

Send the job posting or recruiter message to `POST /check` as `raw_text`. The service analyzes only the text provided in that request.

1. **Extracts structured details** such as company, recruiter, email/domain, job title, salary, payment requests, and distinctive phrases. Groq JSON extraction is used when configured; grounded regex extraction is the fallback.
2. **Checks the message itself** for payment requests, check-deposit traps, crypto or gift-card requests, suspicious chat redirects, and unrealistic compensation.
3. **Checks public evidence** with six concurrent signals:
   - Company physical footprint
   - Official LinkedIn presence
   - Duplicate or syndicated posting fingerprints
   - Fraud, scam, and lawsuit news mentions
   - Recruiter email and claimed-domain integrity
   - Recruiter identity and company affiliation
4. **Calculates a transparent risk score** from 0 to 100 using a base score of 50 plus weighted signal changes.
5. **Returns evidence and a safety verdict** with the extracted fields, each signal finding, search links, and a plain-language summary.

The result is an evidence-based screening aid, not a guarantee of safety or a legal determination. A low-risk result means the available evidence is consistent with a legitimate opportunity; users should still avoid sharing sensitive information until they independently confirm the employer.

### New domain and India-specific evidence

The domain/email check also reports RDAP registration age (young domains are
context only), edit-distance and homoglyph-aware lookalikes against the
discovered official domain, and optional DNS authentication hints (MX, SPF,
and DMARC). DNS uses `dnspython` when installed; missing packages, timeouts,
and WHOIS/RDAP failures produce an unknown hint and **0 points**, never a
failure.

The in-text check highlights India-specific registration, verification,
training, and security-deposit requests, plus WhatsApp- or Telegram-only
contact when no company email/domain is present. Company existence evidence
comes from the existing Google Maps footprint check. These additions do not
change the existing score thresholds or baseline deltas: explicit threat
patterns remain `+10`/`+25`, a verified footprint remains `-15`, and domain
age/DNS metadata alone contributes `0`.
