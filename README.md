# Fake Recruitment Verifier

<div align="center">

![TrueRecruit AI Banner](https://img.shields.io/badge/TrueRecruit%20AI-OSINT%20Threat%20Radar-6366f1?style=for-the-badge&logo=shield&logoColor=white)

<img src="docs/assets/scan-flow.svg" alt="Fake Recruitment Verifier scan flow" width="900" />

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4+-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![SerpApi](https://img.shields.io/badge/SerpApi-Live%20Search%20OSINT-orange?style=flat-square)](https://serpapi.com)
[![CI](https://github.com/kunal-yelgate/fake-recruitment-verifier/actions/workflows/ci.yml/badge.svg)](https://github.com/kunal-yelgate/fake-recruitment-verifier/actions/workflows/ci.yml)

**A transparent screening aid for checking job postings and recruiter messages against public web evidence.**

[Quick start](#quick-start) · [How it works](#how-it-works) · [Sample scans](docs/sample-scans.md) · [API](#api-reference) · [Benchmark](#benchmark-and-accuracy) · [Limitations](#limitations)

</div>

> **Important:** This project is not a fraud detector, legal service, background check, or guarantee that a job is safe. Never send money, identity documents, bank credentials, or one-time passwords because a result looks legitimate.

## Table of contents

- [What the project does](#what-the-project-does)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Features](#features)
- [Repository structure](#repository-structure)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Scoring model](#scoring-model)
- [Benchmark and accuracy](#benchmark-and-accuracy)
- [Testing](#testing)
- [Deploying the frontend](#deploying-the-frontend)
- [Limitations](#limitations)
- [Privacy and security](#privacy-and-security)
- [Troubleshooting](#troubleshooting)

## What the project does

Fake Recruitment Verifier helps a candidate review a job posting or recruiter message before replying. It combines:

- structured extraction of company, recruiter, email, domain, role, salary, address, and payment claims;
- public search evidence from SerpApi;
- grounded reasoning from Groq when configured;
- transparent evidence links and snippets;
- a deterministic 0–100 heuristic risk score;
- plain-English safety guidance.

The application is designed to answer **“what should I verify next?”**, not to make an irreversible **“this is definitely a scam”** decision.

## Architecture

See the [expanded architecture notes](docs/architecture.md) for trust boundaries,
provider fallbacks, and the Mermaid diagram in isolation.

The repository contains a React/Vite browser client and a FastAPI service. The
client sends authenticated requests to the API; provider credentials stay on
the backend and are never bundled into the frontend.

```mermaid
flowchart LR
    UI[React/Vite UI] -->|Clerk bearer token| API[FastAPI API]
    API --> AUTH[Clerk JWT validation]
    API --> EXTRACT[Grounded extraction]
    EXTRACT --> CLAIMS[Claim and search planning]
    CLAIMS --> SEARCH[SerpApi public evidence]
    SEARCH --> JUDGE[Grounded evidence judgments]
    JUDGE --> SCORE[Deterministic scorer]
    SCORE --> API
    API --> CACHE[(SQLite cache)]
```

The claim pipeline is bounded: it validates claims against submitted text,
limits follow-up rounds, records provider provenance, and keeps the numeric
score under deterministic application control. Groq is optional and is used
for extraction, planning, evidence judgments, and explanations; regex and
deterministic fallbacks keep demo mode usable when Groq is unavailable.

Authentication is required for `/check` and `/fetch-url` by default. The
backend validates Clerk JWTs with `CLERK_JWT_KEY` and fails closed when auth is
enabled but no verification key is configured. `REQUIRE_AUTH=False` is intended
only for local development or automated tests. Both analysis endpoints are
rate-limited per client IP by `RATE_LIMIT_PER_MIN` (10 requests/minute by
default); a `429` response includes `Retry-After`.

## How it works

The current analysis pipeline follows this sequence:

```text
Posting or recruiter message
        |
        v
Groq extracts externally verifiable claims
        |
        v
Groq plans targeted Google / News / Maps searches
        |
        v
SerpApi retrieves public evidence
        |
        v
Groq labels evidence:
supports / contradicts / unrelated / ambiguous
        |
        +--> up to 2 bounded follow-up search rounds
        |
        v
Deterministic rules calculate the final risk score
        |
        v
Groq writes a grounded explanation with checked citations
```

### Grounding and safety rules

- A claim must be copied from the submitted text.
- A judgment must cite a returned evidence snippet.
- Mock and failed search responses are never treated as live evidence.
- Follow-up searches are capped in code, not just requested in the prompt.
- Groq does not control the numeric score.
- The deterministic scorer remains the final authority for `risk_score` and `verdict`.
- The API accepts text and can safely fetch public HTTP(S) job pages through
  `POST /fetch-url`. URL fetching blocks private, loopback, link-local, and
  other non-public IP targets, follows only a small bounded number of redirects,
  and enforces timeout, content-type, and response-size limits. OCR uploads are
  not enabled in this phase because the repository has no vetted OCR dependency;
  perform OCR in a separately isolated, trusted client or service and submit the
  resulting text. See [docs/inputs.md](docs/inputs.md) for the URL-import
  workflow, input limits, and the rationale for deferring screenshot OCR.

## Features

- **Claim-driven OSINT:** search plans are tailored to the claims found in each posting.
- **LLM-first extraction:** Groq structured JSON extraction with field-by-field grounding.
- **Regex fallback:** the service remains usable when Groq is unavailable, malformed, or unconfigured.
- **Lookalike-domain checks:** edit-distance and common homoglyph checks against apparent official domains.
- **RDAP context:** domain registration age is shown when available but does not automatically change the score.
- **Evidence audit:** claims, queries, source status, snippets, judgments, follow-ups, and citations are returned.
- **Deterministic score:** repeatable rule-based risk score from 0 to 100.
- **Local history:** scan results can be re-opened from browser `localStorage`.
- **Export:** download a Markdown or JSON forensic report.
- **Referral leads:** when appropriate, public LinkedIn search matches may be shown as leads; they are not confirmed employees.
- **Demo mode:** without SerpApi, the app can run with simulated results clearly marked as mock.
- **Privacy-first samples:** the [sample scan gallery](docs/sample-scans.md) uses synthetic,
  non-contactable identities and links back to the in-app presets.

## Demo

There is no hosted demo or recorded video link in this repository yet. Do not
mistake the local demo for live evidence: follow the reproducible walkthrough
in [`demo/script.md`](demo/script.md), start the backend and frontend locally,
and use the preset scans. The banner above is a static, repository-local
workflow illustration rather than a recording.

## Repository structure

```text
fake-recruitment-verifier/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app and POST /check, POST /fetch-url
│   │   ├── models.py           # Pydantic request, response, and audit models
│   │   ├── claim_pipeline.py   # Claims, search plans, evidence, judgments, follow-ups
│   │   ├── extraction.py       # Groq extraction plus grounded regex fallback
│   │   ├── groq_analysis.py    # Groq decisions and domain selection helpers
│   │   ├── serpapi_client.py   # Async SerpApi client and SQLite cache
│   │   ├── signals/             # Modular text and public-search signal helpers
│   │   ├── scoring.py           # Deterministic 0–100 heuristic score
│   │   ├── config.py            # Environment-backed settings
│   │   ├── cache.py             # 24-hour SQLite query cache
│   │   └── url_fetcher.py       # SSRF-safe bounded HTTP(S) text fetcher
│   ├── tests/                  # Backend unit, integration, and pipeline tests
│   ├── benchmark_real_postings.py
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   ├── package.json
│   └── vite.config.js
├── docs/
│   ├── assets/scan-flow.svg    # README workflow illustration
│   ├── architecture.md         # Trust boundaries and Mermaid diagram
│   ├── privacy.md              # Provider and browser-storage privacy note
│   └── sample-scans.md         # Synthetic preset scan gallery
├── .env.example
├── netlify.toml
└── README.md
```

## Quick start

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- Optional: SerpApi API key for live public searches
- Optional: Groq API key for LLM extraction, claim planning, evidence judgment, and explanations

### 1. Clone and enter the repository

```powershell
git clone https://github.com/kunal-yelgate/fake-recruitment-verifier.git
Set-Location fake-recruitment-verifier
```

### 2. Create and activate a Python environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install backend dependencies

Run this from the repository root:

```bash
python -m pip install --require-hashes -r backend/requirements.lock
```

For local development and tests, install the development layer instead:

```bash
python -m pip install --require-hashes -r backend/requirements-dev.lock
```

Anthropic extraction is optional; install its provider layer only when
`ANTHROPIC_API_KEY` is configured:

```bash
python -m pip install -r backend/requirements-optional.txt
```

### 4. Configure environment variables

Copy the template:

PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
SERPAPI_KEY=your_serpapi_key_here
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
HOST=127.0.0.1
PORT=8000
DEBUG=True
REQUIRE_AUTH=False
```

`REQUIRE_AUTH=False` is only for local development without a Clerk JWT
verification key. Keep authentication enabled in deployed environments.

Never commit `.env` or paste API keys into source code, tests, screenshots, issues, or chat. If a key is exposed, revoke it and create a replacement.

### 5. Start the backend

Run from the repository root so the root `.env` is loaded:

```bash
python backend/run.py
```

Backend URLs:

- API: <http://127.0.0.1:8000>
- Health: <http://127.0.0.1:8000/health>
- Swagger: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

### 6. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

The frontend uses `VITE_API_BASE_URL` when provided. For local development, it defaults to the local backend.

## Configuration

| Variable             | Required | Purpose                                                                                                 |
| -------------------- | -------: | ------------------------------------------------------------------------------------------------------- |
| `SERPAPI_KEY`        |       No | Enables live Google, Google News, and Google Maps searches. Without it, results are marked mock.        |
| `GROQ_API_KEY`       |       No | Enables structured extraction, search planning, evidence judgments, follow-ups, and cited explanations. |
| `GROQ_MODEL`         |       No | Groq model name; defaults to `llama-3.3-70b-versatile`.                                                 |
| `HOST`               |       No | Backend bind host; defaults to `127.0.0.1`.                                                             |
| `PORT`               |       No | Backend port; defaults to `8000`.                                                                       |
| `DEBUG`              |       No | Enables development reload behavior.                                                                    |
| `REQUIRE_AUTH`       |       No | Requires a valid Clerk session for scans; enabled by default.                                           |
| `CLERK_JWT_KEY`      |       No | Clerk JWT verification key when authentication is enabled.                                              |
| `RATE_LIMIT_PER_MIN` |       No | Per-IP limit for scan and URL-fetch endpoints; defaults to 10 requests/minute.                          |
| `CORS_ORIGINS`       |       No | Comma-separated browser origins; localhost is the default.                                              |
| `CACHE_DB_PATH`      |       No | SQLite cache location; defaults to `app_cache.db`.                                                      |
| `CACHE_TTL_HOURS`    |       No | Search-cache lifetime; defaults to 24 hours.                                                            |
| `VITE_API_BASE_URL`  |       No | Frontend URL for a deployed FastAPI backend.                                                            |

Groq receives the submitted posting text when enabled. SerpApi receives planned search queries. Configure these providers only if that data sharing is acceptable.

## API reference

### `POST /check`

Request:

```json
{
  "raw_text": "Company: Example Labs\nRecruiter: Jamie Smith\nEmail: jamie@example.com\n..."
}
```

Important response fields:

```json
{
  "risk_score": 62,
  "verdict": "Caution",
  "verdict_badge": "warning",
  "extracted_fields": {
    "company_name": "Example Labs",
    "recruiter_name": "Jamie Smith",
    "claimed_domain": "example.com",
    "contact_email": "jamie@example.com",
    "job_title": "Software Engineer",
    "salary_range": "$120,000 - $150,000 per year",
    "payment_requests": [],
    "extraction_method": "groq"
  },
  "signals": [],
  "claim_audit": {
    "claims": [],
    "search_plan": [],
    "evidence": [],
    "judgments": [],
    "follow_ups": [],
    "explanation": {
      "text": "Verify the employer through its official careers site.",
      "citations": []
    },
    "rounds_completed": 0
  },
  "is_mock": false,
  "data_quality": "live",
  "overall_confidence": "high"
}
```

The exact claims, signals, and citations depend on the submitted posting and provider responses. `risk_score` is a heuristic index, not a probability.

`data_quality` is `live`, `partial`, or `demo`; non-live responses are not
authoritative verdicts. Signal `confidence` values are `pass`, `fail`, or
`unknown`, and `overall_confidence` summarizes evidence coverage.
When provider evidence is unavailable, the API returns `demo` or `partial`
quality and the UI labels the result as unverified rather than presenting a
legitimate/scam conclusion.

### Other endpoints

| Method | Path           | Purpose                                                            |
| ------ | -------------- | ------------------------------------------------------------------ |
| `POST` | `/fetch-url`   | Authenticated, SSRF-safe extraction of text from a public job URL. |
| `GET`  | `/health`      | Health check                                                       |
| `GET`  | `/cache/stats` | SQLite cache statistics                                            |
| `GET`  | `/metrics`     | Prometheus-style cache/provider counters (no user text or secrets) |
| `GET`  | `/docs`        | Interactive Swagger documentation                                  |
| `GET`  | `/redoc`       | ReDoc API documentation                                            |

## Scoring model

The score starts at 50 and is clamped to the range 0–100:

```text
final_score = clamp(50 + sum(signal_deltas), 0, 100)
```

Current bands:

|  Score | Verdict           | Meaning                                                                             |
| -----: | ----------------- | ----------------------------------------------------------------------------------- |
|   0–34 | Likely Legitimate | Few negative signals were found; this does not prove authenticity.                  |
|  35–64 | Caution           | Evidence is mixed, incomplete, or needs manual verification.                        |
| 65–100 | Likely Scam       | Strong warning signals were found; stop and independently verify before proceeding. |

The score is deterministic once the signal judgments are available. Groq may explain or judge evidence, but it does not directly choose the numeric score.

## Benchmark and accuracy

### What was measured

The repository includes [benchmark_real_postings.py](backend/benchmark_real_postings.py), which samples a balanced set from the public [Real or Fake Job Posting Prediction dataset](https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction). The dataset is labeled with `fraudulent=0` or `fraudulent=1`.

Run it only with a valid SerpApi key:

```bash
python backend/benchmark_real_postings.py backend/benchmarks/fake_job_postings.csv \
  --live \
  --seed 42 \
  --per-class 15 \
  --output benchmark-results/run.json
```

Benchmark input, cache, and report paths must resolve inside the repository
root; place downloaded datasets under `backend/benchmarks/`.

The runner:

- selects 15 legitimate and 15 fraudulent postings with a fixed seed;
- currently evaluates the legacy deterministic signal evaluator, not the new claim pipeline;
- rejects mock and provider-error responses;
- may use up to approximately 180 live searches;
- stores metrics and dataset row IDs, not posting text;
- treats only scores `>= 65` as predicted scams.

### Observed result

There is **no complete, valid accuracy score yet**.

The last authorized run stopped after an incomplete prefix because SerpApi returned fallback data:

| Metric             | Incomplete result |
| ------------------ | ----------------: |
| Evaluated postings |          18 of 30 |
| Accuracy           |  **4/18 = 22.2%** |
| True positives     |                 0 |
| False positives    |                 3 |
| True negatives     |                 4 |
| False negatives    |                11 |
| Scam precision     |                0% |
| Scam recall        |                0% |

This **22.2% is not a valid project accuracy score**. It is an incomplete diagnostic that strongly suggests the current hand-authored weights and cutoff need calibration. It must not be generalized to the full dataset, and mock results must never be mixed with live results.

Before claiming accuracy, run a complete benchmark on a held-out sample with live results, inspect duplicate/near-duplicate postings, and report accuracy, balanced accuracy, scam precision, scam recall, specificity, and the confusion matrix.

## Testing

Backend tests:

```bash
$env:PYTHONPATH="backend"; pytest -q
```

macOS/Linux:

```bash
PYTHONPATH=backend pytest -q
```

Frontend production build:

```bash
cd frontend
npm ci
npm run build
npm test
```

The test suite covers extraction, grounded Groq responses, claim grounding,
search limits, provider failures, scoring, signal behavior, the FastAPI
endpoint, and the core frontend authentication/evidence/verdict views. CI
runs backend tests with coverage on Python 3.10, 3.11, and 3.12, plus Ruff
and the frontend install, build, and test suite.

CI and Docker use hash-locked backend dependency files. When changing Python
dependencies, regenerate them from the source requirements with:

```bash
uv pip compile backend/requirements.txt --python-version 3.10 --generate-hashes --output-file backend/requirements.lock
uv pip compile backend/requirements-dev.txt --python-version 3.10 --generate-hashes --output-file backend/requirements-dev.lock
```

### SonarCloud analysis

The CI workflow runs SonarCloud analysis after backend and frontend checks pass.
The organization and project key are set in [`sonar-project.properties`](sonar-project.properties).
Add a SonarCloud analysis token as the `SONAR_TOKEN` Actions secret in the
GitHub repository settings; do not commit or expose the token. Analysis is
skipped for pull requests from forks because GitHub does not provide repository
secrets to those workflows.

## Deploying the backend on Render

The repository includes a Render Blueprint at [`render.yaml`](render.yaml) for
the FastAPI Docker service. In Render, create a **Blueprint** from this
repository and provide the prompted environment variables:

- `SERPAPI_KEY` enables live search; without it, results use demo data.
- `GROQ_API_KEY` is optional; extraction and analysis fall back when it is absent.
- `CLERK_JWT_KEY` is required because authentication is enabled by default.
- `CORS_ORIGINS` should be the exact origin of the deployed frontend, without a
  trailing slash (for example, `https://your-site.netlify.app`).

If deploying the existing native Python service instead of the Blueprint, set
its Root Directory to `backend` and keep its build command as
`pip install -r requirements.txt`. The [`backend/.python-version`](backend/.python-version)
pin selects Python 3.12.10, which has prebuilt wheels for the pinned
`pydantic-core` dependency and avoids failing Rust source builds on newer
default Python versions.

Render assigns the service's `PORT` automatically. The Docker image binds to
that port and uses `/health` as its health check. After deployment, confirm
`https://<your-render-service>.onrender.com/health` returns a healthy response.

## Deploying the frontend

The frontend is configured for **Netlify** through [`netlify.toml`](netlify.toml).

1. Connect `kunal-yelgate/fake-recruitment-verifier` to Netlify and select
   `main` as its production branch; [`netlify.toml`](netlify.toml) configures
   the frontend base directory, build command, publish directory, and SPA fallback.
2. In Netlify's site environment variables, set `VITE_API_BASE_URL` to the
   deployed FastAPI backend URL and `VITE_CLERK_PUBLISHABLE_KEY` to the Clerk
   publishable key for the same Clerk instance used to issue backend JWTs.
   These values must be set before the production build because Vite embeds
   `VITE_` variables in the frontend bundle.
3. Add the deployed Netlify origin to the Render service's `CORS_ORIGINS`
   environment variable, then redeploy the backend.

Keep all provider and Clerk verification keys in the backend's deployment
environment; never put them in frontend `VITE_` variables.

## Limitations

- A small legitimate startup may have little or no Maps, LinkedIn, or news footprint and can receive caution signals.
- A scammer can copy a real company name, domain, job description, or employee identity.
- A company-domain match does not prove that the sender is employed by that company.
- Public search engines can return stale, irrelevant, duplicated, or misleading results.
- Groq can misunderstand messy, translated, or OCR-derived text; grounded validation reduces invention but does not guarantee correctness.
- Search-provider outages, quota limits, and rate limits can reduce evidence coverage.
- RDAP age is context only and does not prove that a domain is fraudulent.
- The current numeric weights are hand-authored heuristics and are not statistically calibrated.
- The current benchmark is incomplete and cannot support an accuracy claim.
- Screenshot upload and OCR are not implemented in the API.

## Privacy and security

Read the full [privacy note](docs/privacy.md) before enabling live providers.
In short, scan text stays in the browser history until the user clears it,
while enabled Groq and SerpApi integrations receive the portions of a scan
needed for their configured requests. Demo mode does not make provider data
sharing live.

- Do not commit `.env`, API keys, recruiter personal data, or private job documents.
- Use synthetic text when testing provider integrations.
- Treat public LinkedIn matches as possible referral leads, not confirmed employee identities.
- Verify the employer using a trusted company website that you navigate to independently.
- Never pay to apply for a job or deposit a check on behalf of an employer.
- If a provider key is exposed, revoke it immediately and replace it.

## Troubleshooting

### The frontend says “Failed to fetch”

Make sure the backend is running from the repository root:

```bash
python backend/run.py
```

Then check <http://127.0.0.1:8000/health>.

### Results say demo/mock mode

`SERPAPI_KEY` is missing, empty, invalid, or the provider returned a fallback response. Mock results are intentionally labeled and are not valid live evidence.

### Groq extraction is not shown

Check `GROQ_API_KEY`, restart the backend after editing `.env`, and inspect the returned `extraction_method`. The service falls back to regex when Groq fails.

### PowerShell cannot activate `.venv`

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```
