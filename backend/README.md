# Fake Recruiter Verifier - Backend Service

FastAPI-powered asynchronous verification service backed by SerpApi live search intelligence and SQLite caching.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the development server
python run.py
# Or with uvicorn directly:
uvicorn app.main:app --reload --port 8000
```

## API Documentation

- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc UI: `http://127.0.0.1:8000/redoc`

## How the project works

Send the job posting or recruiter message to `POST /check` as `raw_text`. The service analyzes only the text provided in that request.

1. **Extracts details** such as company, recruiter, email/domain, job title, and distinctive phrases.
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
