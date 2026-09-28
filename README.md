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
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

**Cross-check job postings and recruiter outreach against live web intelligence to detect phishing, fake check fraud, lookalike domains, and recruiter impersonation in real-time.**

[Quickstart](#quick-start) • [Architecture](#repository-architecture) • [OSINT Engines](#serpapi-osint-engines) • [Scoring Logic](#scoring-engine) • [API Docs](#api-reference)

</div>

---

## 💡 Why This is Different

Most job-scam checkers (LoopCV, JobScamScore, JobMeter) only classify the _internal text_ of a posting against known scam keywords. That misses the strongest scam signature: **whether the world outside the posting corroborates it.**

TrueRecruit AI cross-checks the posting against live multi-engine search data:

- 🗺️ **Physical Footprint**: Does the company have a registered Google Maps listing or headquarters address?
- 👔 **Corporate Authority**: Does it have an active, verified LinkedIn company presence?
- 🌐 **Global Syndication Fingerprint**: Is the exact phrase syndicated across pastebins and spam forums?
- 🔒 **Domain & Email Integrity**: Is the recruiter using a free webmail address (`@gmail.com`) or a spoofed lookalike domain (`amazon-careers.net` vs `amazon.com`)?
- 📰 **Threat Intelligence**: Are there recent news reports, FTC consumer alerts, or lawsuit complaints?
- 👤 **Recruiter Affiliation**: Does the named recruiter have a public professional record connecting them to the hiring company?

The result combines hand-written checks of the message with public web-search signals. Each finding and search query is shown for review. The point values are hand-authored heuristics, not statistically calibrated weights, and the score is **not a probability** that a job is a scam.

---

## ⚡ Key Features

- **Cyber Threat Radar UI**: Radial animated risk gauge (0–100), trust tier badges, and live telemetry vector distribution.
- **Parallel OSINT Probe Visualizer**: Real-time multi-step animation tracking all 6 engines during analysis.
- **Searchable Evidence Matrix**: Filter by status (_Threats_, _Verified_, _All_), search findings, and inspect raw query parameters.
- **Extracted Entity Credentials**: Automatic NLP extraction for Company, Role, Recruiter, Claimed Domain, and Unique Phrases.
- **Local Scan History**: Persistent `localStorage` drawer for 1-click scan reloads without re-querying.
- **Forensic Report Exporter**: 1-click export to formatted **Markdown (.md)** or **JSON (.json)** with instant download.
- **Candidate Safety Advisory**: Actionable checklists with direct links to the **FTC Fraud Portal** and **FBI IC3 Complaint Center**.

---

## 🔍 SerpApi OSINT Engines

| Signal                         | Engine        | What it checks                                                                                   | Current heuristic point changes                                                                 |
| ------------------------------ | ------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| **In-posting threat patterns** | Text rules    | Check deposits, suspicious chat redirects, gift cards/crypto, and some unusually high pay claims | `+25` critical / `+10` one warning / `-10` none found                                           |
| **Company footprint**          | `google_maps` | Whether a matching public business listing is found                                              | `-15` found / `+10` not found                                                                   |
| **LinkedIn presence**          | `google`      | Whether a company page is found                                                                  | `-15` found / `+12` not found                                                                   |
| **Duplicate posting**          | `google`      | Exact phrase results and suspicious posting sites                                                | `+18` suspicious or widespread copies / `-8` one result / `-4` no widespread copies             |
| **Fraud news mentions**        | `google_news` | Search results for fraud, scam, or lawsuit reports                                               | `+20` result treated as a direct complaint / `-5` no result or impersonation warning            |
| **Domain and email match**     | `google`      | Free email, claimed domain, and search result domain                                             | `+25` free email / `+22` domain mismatch / `-15` matching domain / `+5` no domain / `0` unclear |
| **Recruiter identity**         | `google`      | Public evidence connecting the named recruiter to the company                                    | `-12` connection found / `+10` not found                                                        |

These point values are the current implementation, not learned from labeled data. Missing search results can reflect limited public information and do not by themselves prove fraud.

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
│   │   ├── scoring.py                  # Heuristic risk scoring engine (0–100)
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
- _(Optional)_ [SerpApi API Key](https://serpapi.com) (100 free searches/mo). When omitted, the app operates in **Demo Simulation Mode**.

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

- For `https://truerecruit-test.netlify.app`, ensure the backend CORS allowlist includes that exact origin.

4. Click **Deploy**!

---

## 🧪 Running Tests

Run the full automated test suite with pytest:

```bash
pytest -v
```

The backend suite currently contains 15 unit, functional, extraction, scoring, and endpoint tests.

---

## 📊 Scoring Engine

The heuristic risk score begins at **50 points**, adds the point changes shown above, and is clamped to `[0, 100]`:

$$\text{Final Risk Score} = \text{clamp}\left(50 + \sum \Delta_{\text{signals}},\, 0,\, 100\right)$$

- **`>= 65`** → 🚨 **Likely Scam** (higher-risk warning signs)
- **`35 – 64`** → ⚠️ **Caution** (mixed results or too little evidence)
- **`< 35`** → 🛡️ **Likely Legitimate** (lower-risk signals found)

### Calibration and accuracy

The point values and cutoffs are hand-authored heuristics. They have **not** been calibrated or validated on a held-out set of real job postings, so this project does not claim a measured accuracy percentage. The two files in `backend/tests/fixtures/` are functional test examples, not independent real-world validation data. The 0–100 result is a risk index, not a fraud probability; a low score does not prove that a recruiter or job is genuine.

#### Reproducing a benchmark

The [Real or Fake Job Posting Prediction dataset](https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction) describes about 18,000 postings and is labeled CC0 on its Kaggle page. Download and extract `fake_job_postings.csv`, configure `SERPAPI_KEY`, then run from the repository root:

```bash
python backend/benchmark_real_postings.py /path/to/fake_job_postings.csv --live --seed 42 --per-class 15 --output benchmark-results/run.json
```

This samples 15 postings of each label, uses regex extraction, and requires live SerpApi results. The runner stops without reporting accuracy if any signal falls back to mock/error data. The JSON report contains dataset row numbers, labels, scores, and metrics but does not copy posting text. Each run may use up to about 180 live searches; check your provider quota before running. The decision rule treats only scores of 65 or above as scam; `Caution` counts as not-scam for the reported binary metrics.

#### Current validation status

No valid accuracy figure is available. A live run was attempted on a fixed 30-posting sample, but SerpApi returned a mock fallback before all 30 postings could be scored. The incomplete sample is not reported as accuracy. The provider's demo responses must not be mixed with live-search results. Until a complete run succeeds, the weights and cutoffs remain uncalibrated; do not interpret the score as a probability.

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
  "summary": "High risk score (77/100). The posting triggered scam warning signs: Recruiter uses free webmail...",
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
