# Privacy note

TrueRecruit is designed for cautious, user-directed checks. It is not a
private document vault, and the project does not promise that third-party
providers will retain no data.

## What is processed

When a scan is submitted, the API receives the text needed to extract claims,
plan searches, and return a result. If `GROQ_API_KEY` is configured, relevant
scan text is sent to Groq for the enabled analysis steps. If `SERPAPI_KEY` is
configured, claim-derived search queries are sent to SerpApi. Public result
snippets and URLs are returned to the browser as evidence.

The frontend stores completed scans in browser `localStorage` so the history
drawer can reopen them. Use **Clear history** (or clear site storage) to
remove those local copies. The backend cache is separate and expires according
to `CACHE_TTL_HOURS`; it should be treated as operational provider cache, not
as a deletion guarantee.

## What not to submit

Do not paste resumes, identity documents, addresses, phone numbers, bank
details, one-time passwords, private recruiter correspondence, or other
confidential material. Redact names and contact details when a synthetic
example is sufficient. Never include API keys in scans, screenshots, issues,
or commits.

## Provider and deployment choices

Run without provider keys for clearly labelled demo mode. Before enabling live
providers, review their current terms and retention policies and decide
whether the transfer is appropriate for the text being checked. Deployments
should use HTTPS, restrict CORS to known frontend origins, keep `.env` out of
version control, and protect logs and the SQLite cache as sensitive
operational data.

The application can surface public evidence, but a public profile or search
match is not proof of identity. Verify an employer through a trusted website
you navigate to independently, and never send money or sensitive information
because a score looks safe.
