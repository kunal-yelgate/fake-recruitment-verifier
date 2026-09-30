# Architecture and trust boundaries

TrueRecruit is a screening aid, not an identity authority. The browser owns
the submitted text and presentation state; the FastAPI service owns provider
credentials, bounded searches, evidence normalization, and deterministic
scoring.

```mermaid
flowchart LR
    B[Candidate browser<br/>React/Vite] -->|Clerk bearer token + scan text| A[FastAPI API]
    A --> V[Input validation<br/>rate limit + auth]
    V --> X[Grounded extraction]
    X --> P[Claim and search planning]
    P --> S[SerpApi<br/>public web evidence]
    S --> J[Grounded evidence judgments]
    J --> R[Deterministic risk scorer]
    R --> A
    A -->|redacted result + provenance| B
    A --> C[(SQLite cache<br/>query keys only)]
    X -. optional .-> G[Groq<br/>extraction / explanation]
    J -. optional .-> G
```

## Data boundaries

- **Browser:** stores scan history in local `localStorage`. Clearing browser
  storage or using the history controls removes those local copies.
- **API:** receives the submitted text for the duration of a scan. It keeps
  provider credentials server-side and does not bundle them into the frontend.
- **Groq:** receives submitted text when configured for extraction, planning,
  evidence judgments, or explanations. Do not enable it for confidential
  documents unless that transfer is acceptable.
- **SerpApi:** receives bounded search queries derived from extracted claims,
  not API keys or the full posting by default.
- **SQLite cache:** stores provider query/result cache entries for the configured
  TTL. It is an operational cache, not a user-facing archive.

Mock or failed provider responses are marked as `demo` or `partial` and are
never presented as live evidence. The deterministic scorer remains in control
of the numeric score.
