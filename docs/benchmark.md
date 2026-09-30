# Calibration benchmark

The checked-in corpus at
[`backend/benchmarks/dataset/postings.json`](../backend/benchmarks/dataset/postings.json)
contains 102 synthetic, privacy-safe postings: 34 scam, 34 legitimate, and
34 ambiguous examples. It includes Indian-style registration-fee, security
deposit, and WhatsApp recruitment patterns without personal data.

The numeric scorer remains hand-tuned. The corpus is a calibration foundation,
not a claim of production accuracy.

## Reproduce the offline metrics

From the repository root, run:

```powershell
.\.venv\Scripts\python.exe backend\benchmark_synthetic_dataset.py
```

The same report is available through the main benchmark entry point:

```powershell
.\.venv\Scripts\python.exe backend\benchmark_real_postings.py --synthetic `
  --output docs\benchmark-results.json
```

The command evaluates all 102 rows without network access and prints accuracy,
macro precision, macro recall, macro F1, per-class precision/recall/F1, and a
multiclass confusion matrix. To save the row-level output:

```powershell
.\.venv\Scripts\python.exe backend\benchmark_synthetic_dataset.py `
  --output benchmark-synthetic-report.json
```

The matrix uses actual labels as rows and predicted labels as columns, in the
order `scam`, `legit`, `ambiguous`. Predictions map `Likely Scam` to `scam`,
`Likely Legitimate` to `legit`, and `Caution` to `ambiguous`.

## Limitations

This is an offline regression benchmark for the deterministic in-posting threat
signal only; it does not exercise live SerpApi signals, provider failures, or
the full production pipeline. The examples are synthetic, repeated patterns
are intentionally simple, and the labels are not an independently adjudicated
sample. Metrics therefore do not estimate real-world accuracy or generalization.
No scoring weights are tuned by the benchmark.

Current synthetic baseline: 66.7% accuracy and 0.556 macro-F1. Scam
precision/recall/F1 are each 1.0; the conservative scorer maps the legitimate
examples to the ambiguous band. These figures are regression metrics only.

## Weight calibration decision

No scoring weights were changed from this benchmark. The corpus is synthetic,
repetitive, and exercises only the deterministic text-threat signal, so using
it to tune production weights would overfit the fixture rather than improve
generalization.

| Version | Accuracy | Macro-F1 | Weight change |
|---|---:|---:|---|
| Baseline | 66.7% | 0.556 | None |
| Calibrated | 66.7% | 0.556 | Not applied; insufficient real-world evidence |

## Calibration decision

The benchmark was run before and after review of `app/scoring.py`. The weights
were deliberately left unchanged:

| Measure | Before | After | Decision |
| --- | ---: | ---: | --- |
| Base score | 50 | 50 | Unchanged; the corpus does not establish a better neutral prior |
| In-posting threat delta (none / one / critical) | -10 / +10 / +25 | -10 / +10 / +25 | Unchanged; the synthetic corpus is not safe evidence for production weights |
| Scam threshold | 65 | 65 | Unchanged; preserving the stated formula and threshold |
| Caution lower bound | 35 | 35 | Unchanged; preserving the stated formula and threshold |
| Accuracy | 66.7% | 66.7% | No measured before/after improvement |
| Macro-F1 | 0.556 | 0.556 | No measured before/after improvement |

Although lowering the no-threat score far enough could move the synthetic
legitimate rows below the caution threshold, that would optimize repeated,
synthetically authored wording rather than independently adjudicated examples.
The fixture exercises only the deterministic text-threat signal, labels are not
production ground truth, and all legitimate rows currently share the same
conservative caution outcome. That is insufficient evidence to change weights
or thresholds safely. The unchanged values are therefore the calibrated
baseline for future, independently reviewed data.
