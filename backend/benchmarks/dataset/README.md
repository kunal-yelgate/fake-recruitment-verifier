# Benchmark postings

`postings.json` is a **synthetic, deterministic fixture** for calibrating and
regression-testing the verifier. It was generated for this repository; it was
not copied from job boards, messages, or user reports. The records use generic
employer and role names, and contain no real contact details, URLs, names,
addresses, or other personal data.

Each record has:

- `id`: stable synthetic identifier
- `label`: one of `scam`, `legit`, or `ambiguous`
- `text`: the posting/message to classify

The fixture includes Indian-style currency and hiring language, payment/fee
requests, WhatsApp-only contact, urgency, fake-offer patterns, ordinary
no-payment applications, and intentionally incomplete postings. It is designed
to exercise signals, not to represent prevalence or provide ground truth for
real-world decisions. Do not use it to make production verdicts or infer
scoring weights.
