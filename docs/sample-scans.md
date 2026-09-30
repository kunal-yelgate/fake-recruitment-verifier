# Sample scans

These examples are intentionally synthetic and safe to run in demo mode. They
are the same style of presets exposed by the frontend scanner; they are not
claims about the named organizations and should not be used as evidence about
any real person or employer.

| Preset | What it demonstrates | Expected review focus |
| --- | --- | --- |
| **Fake check / equipment** | A made-up staffing message asks a candidate to deposit an equipment check and uses a free mailbox. | Stop, do not deposit a check, and independently verify the employer. |
| **Lookalike domain** | A fictional outreach flow combines executive impersonation language with a lookalike domain. | Navigate to the official company site yourself; do not use the supplied link. |
| **Telegram / crypto payout** | Urgency, instant hiring, and a request to move the conversation to Telegram. | Treat payment, wallet, and pressure signals as a reason to pause. |
| **Enterprise-style control** | A public-style job description with a conventional application path. | A low score is not proof; verify through the company’s independently found careers page. |

The source text lives in [`frontend/src/constants/samples.js`](../frontend/src/constants/samples.js)
so the UI and this page can be reviewed together. Sample names and contact
addresses are fictionalized; do not add real recruiter data to this repository.

## Reproducible local walkthrough

1. Start the backend and frontend using the [README quick start](../README.md#quick-start).
2. Sign in if authentication is enabled.
3. Load one of the preset examples in the scanner and run it without provider
   keys first. Confirm that the result is labelled `demo`/mock.
4. Clear scan history after testing if the browser is shared.

For a narration-ready sequence, see [`demo/script.md`](../demo/script.md).
