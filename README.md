Job Scam & Fake Recruiter Verifier

<div align="center">

![TrueRecruit AI Banner](https://img.shields.io/badge/TrueRecruit%20AI-OSINT%20Threat%20Radar-6366f1?style=for-the-badge&logo=shield&logoColor=white)
<br/>
<br/>

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4+-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![SerpApi](https://img.shields.io/badge/SerpApi-Live%20Search%20OSINT-orange?style=flat-square)](https://serpapi.com)
[![Tests](https://img.shields.io/badge/Pytest-10%2F10%20Passing-brightgreen?style=flat-square)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

**Cross-check job postings and recruiter outreach against live web intelligence to detect phishing, fake check fraud, lookalike domains, and recruiter impersonation in real-time.**

[Quickstart](#quick-start) • [Architecture](#repository-architecture) • [OSINT Engines](#serpapi-osint-engines) • [Scoring Logic](#scoring-engine) • [API Docs](#api-reference)

</div>

---

## 💡 Why This is Different

Most job-scam checkers (LoopCV, JobScamScore, JobMeter) only classify the *internal text* of a posting against known scam keywords. That misses the strongest scam signature: **whether the world outside the posting corroborates it.**

TrueRecruit AI cross-checks the posting against live multi-engine search data:
- 🗺️ **Physical Footprint**: Does the company have a registered Google Maps listing or headquarters address?
- 👔 **Corporate Authority**: Does it have an active, verified LinkedIn company presence?
- 🌐 **Global Syndication Fingerprint**: Is the exact phrase syndicated across pastebins and spam forums?
- 🔒 **Domain & Email Integrity**: Is the recruiter using a free webmail address (`@gmail.com`) or a spoofed lookalike domain (`amazon-careers.net` vs `amazon.com`)?
- 📰 **Threat Intelligence**: Are there recent news reports, FTC consumer alerts, or lawsuit complaints?
- 👤 **Recruiter Affiliation**: Does the named recruiter have a public professional record connecting them to the hiring company?

Every verdict is a **transparent, weighted sum of live OSINT probes** — not an opaque LLM hallucination — and every evidence line links directly to the real-world search query that verified or flagged it.

---

## ⚡ Key Features

- **Cyber Threat Radar UI**: Radial animated risk gauge (0–100), trust tier badges, and live telemetry vector distribution.
- **Parallel OSINT Probe Visualizer**: Real-time multi-step animation tracking all 6 engines during analysis.
- **Searchable Evidence Matrix**: Filter by status (*Threats*, *Verified*, *All*), search findings, and inspect raw query parameters.
- **Extracted Entity Credentials**: Automatic NLP extraction for Company, Role, Recruiter, Claimed Domain, and Unique Phrases.
- **Local Scan History**: Persistent `localStorage` drawer for 1-click scan reloads without re-querying.
- **Forensic Report Exporter**: 1-click export to formatted **Markdown (.md)** or **JSON (.json)** with instant download.
- **Candidate Safety Advisory**: Actionable checklists with direct links to the **FTC Fraud Portal** and **FBI IC3 Complaint Center**.

---

## 🔍 SerpApi OSINT Engines

| OSINT Signal | Engine | Primary Objective | Scoring Impact |
|---|---|---|---|
| **Company Footprint** | `google_maps` | Verifies physical headquarters & place existence | `-15` (Pass) / `+10` (Missing) |
| **LinkedIn Presence** | `google` (`site:linkedin.com`) | Confirms active corporate identity & headcount | `-15` (Pass) / `+12` (Missing) |
| **Duplicate Posting** | `google` (Exact Match) | Detects cross-forum automated spam syndication | `+18` (Spam) / `-8` (Unique) |
| **News Fraud Mentions** | `google_news` | Discovers FTC/BBB alerts and lawsuit complaints | `+20` (Alert) / `-5` (Clean) |
| **Domain & Email Match** | `google` | Flags `@gmail/@yahoo` recruiters & lookalike domains | `+25` (Mismatch) / `-10` (Match) |
| **Recruiter Identity** | `google` | Validates recruiter professional record & company link | `-12` (Affiliated) / `+10` (Unverified) |

---

## 🏗️ Repository Architecture

```
fake-recruiter-verifier/
├── backend/                            # Isolated Backend workspace
│   ├── app/                            # FastAPI core application logic
│   │   ├── main.py                     # FastAPI application entrypoint & routing
│   │   ├── config.py                   # Pydantic settings & environment configuration
│   │   ├── models.py                   # Pydantic request/response schemas
│   │   ├── extraction.py               # Posting text → structured entities (Regex/LLM)
│   │   ├── signals.py                  # 6 parallel SerpApi OSINT verification probes
│   │   ├── scoring.py                  # Transparent weighted scoring engine (0–100)
│   │   ├── cache.py                    # SQLite 24h query cache with TTL & stats
│   │   └── serpapi_client.py           # Async SerpApi client with local SQLite cache & mock fallback
│   ├── tests/                          # Backend automated test suite (pytest)
│   │   ├── test_scoring.py             # Unit tests for scoring formula & clamping bounds
│   │   ├── test_extraction.py          # Entity extraction fallback tests
│   │   ├── test_functional.py          # Functional end-to-end and FastAPI endpoint tests
│   │   └── fixtures/                   # Realistic scam & legitimate test postings
│   ├── run.py                          # Dedicated backend launcher (`python run.py`)
│   ├── requirements.txt                # Python dependencies
│   └── README.md                       # Backend service documentation
│
├── frontend/                           # React + Vite + Tailwind Enterprise Frontend
│   ├── index.html                      # HTML5 entrypoint with preconnected fonts
│   ├── package.json                    # React 18, Lucide icons, Vite, Tailwind CSS
│   ├── vite.config.js                  # Vite configuration & dev server proxy
│   ├── tailwind.config.js              # Theme tokens & glassmorphism utilities
│   └── src/
│       ├── main.jsx                    # React DOM root
│       ├── App.jsx                     # Root application coordinator
│       ├── styles/
│       │   └── index.css               # Design system tokens, glassmorphism, radar pulse
│       ├── components/
│       │   ├── ui/                     # Base primitives: Button, Badge, Card, Tabs, Modal, ProgressRing
│       │   ├── layouts/                # Navbar (Status, History, Theme) and Footer
│       │   └── features/
│       │       ├── Scanner/            # PostingInput, PresetSelector, ScanProgressStepper
│       │       ├── Results/            # VerdictHero, ThreatRadar, SafetyChecklist, ExportReportModal
│       │       ├── Evidence/           # EvidenceTable, SignalRow
│       │       ├── Entities/           # EntitiesGrid, DomainMismatchAlert
│       │       └── History/            # ScanHistoryDrawer
│       ├── hooks/                      # useVerifier, useScanHistory, useClipboard
│       ├── services/                   # api.js, reportGenerator.js
│       └── constants/                  # samples.js, signalDefinitions.js
│
├── app/                                # Top-level Python package (backward compatible)
├── tests/                              # Top-level Pytest suite
├── .env.example                        # Environment variable template
├── .gitignore
├── requirements.txt                    # Root Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & `npm`
- *(Optional)* [SerpApi API Key](https://serpapi.com) (100 free searches/mo). When omitted, the app operates in **Demo Simulation Mode**.

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
SERPAPI_KEY=your_actual_serpapi_key_here
```

### 3. Start Backend (FastAPI)

```bash
# Option A: From project root
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Option B: From backend folder
cd backend
pip install -r requirements.txt
python run.py
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive Swagger docs: `http://127.0.0.1:8000/docs`

### 4. Start Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 🌐 Deploy Frontend to Vercel

The frontend is fully configured for seamless, zero-config deployment to [Vercel](https://vercel.com):

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/kunal-yelgate/fake-recruitment-verifier)

### Deployment Steps:
1. **Import Repository**: In your Vercel dashboard, click **Add New Project** and select this repository.
2. **Build Settings**: Vercel automatically detects the included `vercel.json` and Vite configuration.
   - **Framework Preset:** Vite
   - **Root Directory:** `./` (or `frontend`)
   - **Build Command:** `cd frontend && npm install && npm run build`
   - **Output Directory:** `frontend/dist`
3. **Environment Variables**:
   - Add `VITE_API_BASE_URL` with your deployed backend URL (e.g. `https://your-backend-api.onrender.com` or Railway/Fly.io URL).
4. Click **Deploy**!

---

## 🧪 Running Tests

Run the full automated test suite with pytest:

```bash
pytest -v
```

All 10 unit, functional, extraction, scoring, and endpoint tests run in ~1 second.

---

## 📊 Scoring Engine

The risk score begins at a neutral base of **50 points** and is adjusted by summing delta points from each verified signal, clamped to `[0, 100]`:

$$\text{Final Risk Score} = \text{clamp}\left(50 + \sum \Delta_{\text{signals}},\, 0,\, 100\right)$$

- **`>= 65`** → 🚨 **Likely Scam** (Critical fraud vectors detected; high candidate threat)
- **`35 – 64`** → ⚠️ **Caution** (Mixed or uncorroborated corporate traces)
- **`< 35`** → 🛡️ **Likely Legitimate** (Strong corroborated corporate footprint)

---

## 📡 API Reference

### `POST /check`
Analyze raw job posting text and run parallel OSINT probes.

**Request:**
```json
{
  "raw_text": "Job Title: Remote Data Entry Clerk\nCompany: Apex Global Staffing\nSalary: $50/hr\nApply: marcus.vance.careers@gmail.com"
}
```

**Response:**
```json
{
  "risk_score": 77,
  "verdict": "Likely Scam",
  "verdict_badge": "danger",
  "base_score": 50,
  "extracted_fields": {
    "company_name": "Apex Global Staffing",
    "recruiter_name": "Marcus Vance",
    "contact_email": "marcus.vance.careers@gmail.com",
    "claimed_domain": "gmail.com",
    "job_title": "Remote Data Entry Clerk",
    "extraction_method": "regex"
  },
  "signals": [
    {
      "signal_key": "domain_match",
      "signal_name": "Domain & Email Match",
      "engine": "google",
      "score_delta": 25,
      "status": "fail",
      "finding": "High Risk: Recruiter email uses a free webmail domain (@gmail.com) instead of an official company email domain.",
      "query_used": "\"Apex Global Staffing\" official website",
      "evidence_url": null,
      "search_url": "https://www.google.com/search?q=%22Apex+Global+Staffing%22+official+website"
    }
  ],
  "summary": "High scam probability (77/100). The posting triggered critical fraud signals: Recruiter uses free webmail...",
  "is_mock": false,
  "execution_time_seconds": 1.42
}
```

### `GET /health`
Returns service status and timestamp.

### `GET /cache/stats`
Returns SQLite 24h query cache statistics.

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for more information.
