"""Run a small, reproducible live-search benchmark on the Kaggle job dataset.

This script makes live SerpApi requests. A balanced 30-posting run can use up
to 180 searches, depending on the cache and available posting details.
"""

import argparse
import asyncio
import csv
import json
import random
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.cache import QueryCache
from app.config import settings
from app.extraction import extract_with_regex
from app.scoring import SCAM_THRESHOLD, calculate_risk_score
import app.serpapi_client as serpapi_module
from app.serpapi_client import serpapi_client
from app.signals import evaluate_all_signals


DATASET_URL = "https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction"
TEXT_COLUMNS = (
    "title",
    "company_profile",
    "description",
    "requirements",
    "benefits",
    "location",
    "department",
    "salary_range",
    "employment_type",
    "required_experience",
    "required_education",
    "industry",
    "function",
)


def load_sample(csv_path: Path, per_class: int, seed: int) -> list[tuple[int, int, dict[str, str]]]:
    labeled_rows: dict[int, list[tuple[int, dict[str, str]]]] = {0: [], 1: []}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames or "fraudulent" not in reader.fieldnames:
            raise ValueError("CSV must contain the dataset's 'fraudulent' label column.")

        for row_number, row in enumerate(reader, start=1):
            try:
                label = int(row["fraudulent"] or "")
            except (TypeError, ValueError):
                continue
            if label in labeled_rows:
                labeled_rows[label].append((row_number, row))

    for label, rows in labeled_rows.items():
        if len(rows) < per_class:
            raise ValueError(
                f"Need {per_class} rows for label {label}; found {len(rows)}."
            )

    rng = random.Random(seed)
    sample = [
        (label, row_number, row)
        for label, rows in labeled_rows.items()
        for row_number, row in rng.sample(rows, per_class)
    ]
    rng.shuffle(sample)
    return sample


def make_posting_text(row: dict[str, str]) -> str:
    return "\n\n".join(
        f"{column.replace('_', ' ').title()}: {row[column].strip()}"
        for column in TEXT_COLUMNS
        if row.get(column, "").strip()
    )


def calculate_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    true_positive = sum(item["label"] == 1 and item["predicted_scam"] for item in results)
    false_positive = sum(item["label"] == 0 and item["predicted_scam"] for item in results)
    true_negative = sum(item["label"] == 0 and not item["predicted_scam"] for item in results)
    false_negative = sum(item["label"] == 1 and not item["predicted_scam"] for item in results)
    count = len(results)
    accuracy = (true_positive + true_negative) / count if count else 0.0
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    specificity = true_negative / (true_negative + false_positive) if true_negative + false_positive else 0.0

    return {
        "sample_size": count,
        "accuracy": accuracy,
        "balanced_accuracy": (recall + specificity) / 2,
        "scam_precision": precision,
        "scam_recall": recall,
        "confusion_matrix": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "true_negative": true_negative,
            "false_negative": false_negative,
        },
    }


async def run_live_benchmark(
    sample: list[tuple[int, int, dict[str, str]]],
    csv_path: Path,
    seed: int,
    output_path: Path | None,
    cache_db: Path | None,
) -> dict[str, Any]:
    original_search = serpapi_client.search
    original_cache = serpapi_module.cache
    search_counts = {"live_requests": 0, "cached_live_results": 0, "fallbacks": 0}
    fallback_types: set[str] = set()
    results = []

    async def require_live_search(engine: str, params: dict[str, Any]) -> dict[str, Any]:
        query_params = {"engine": engine, **params}
        was_cached = serpapi_module.cache.get(engine, query_params) is not None
        response = await original_search(engine, params)
        if response.get("_is_mock") or response.get("_api_error"):
            search_counts["fallbacks"] += 1
            api_error = str(response.get("_api_error", "")).lower()
            status = re.search(r"http\s+(\d{3})", api_error)
            if status:
                fallback_types.add(f"HTTP {status.group(1)}")
            elif "timeout" in api_error or "timed out" in api_error:
                fallback_types.add("request timeout")
            elif api_error:
                fallback_types.add("request error")
            else:
                fallback_types.add("mock response")
        elif was_cached:
            search_counts["cached_live_results"] += 1
        else:
            search_counts["live_requests"] += 1
        return response

    temp_dir = None
    if cache_db:
        cache_db.parent.mkdir(parents=True, exist_ok=True)
        cache_path = cache_db
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="truerecruit-benchmark-")
        cache_path = Path(temp_dir.name) / "benchmark.sqlite"

    serpapi_module.cache = QueryCache(str(cache_path))
    serpapi_client.search = require_live_search
    try:
        for label, row_number, row in sample:
            posting_text = make_posting_text(row)
            if len(posting_text.strip()) < 10:
                raise ValueError(f"Dataset row {row_number} has too little posting text.")

            fields = extract_with_regex(posting_text)
            signals = await evaluate_all_signals(fields, posting_text)
            if search_counts["fallbacks"]:
                details = ", ".join(sorted(fallback_types))
                raise RuntimeError(
                    f"SerpApi returned mock/fallback data ({details}). "
                    "The benchmark stopped without recording accuracy."
                )

            score, verdict, _, _ = calculate_risk_score(signals)
            results.append(
                {
                    "dataset_row": row_number,
                    "label": label,
                    "score": score,
                    "verdict": verdict,
                    "predicted_scam": score >= SCAM_THRESHOLD,
                }
            )
            print(
                f"{len(results):02}/{len(sample)}: label={label} "
                f"score={score} verdict={verdict} "
                f"live_requests={search_counts['live_requests']} "
                f"cached={search_counts['cached_live_results']}"
            )
    finally:
        serpapi_client.search = original_search
        serpapi_module.cache = original_cache
        if temp_dir:
            temp_dir.cleanup()

    metrics = calculate_metrics(results)
    report = {
        "dataset": DATASET_URL,
        "csv_file_name": csv_path.name,
        "seed": seed,
        "sample_per_class": len(sample) // 2,
        "decision_rule": f"score >= {SCAM_THRESHOLD} predicts scam; caution counts as not scam",
        "extraction": "regex",
        "search_mode": "live SerpApi only; mock/fallback responses are rejected",
        "search_counts": search_counts,
        "metrics": metrics,
        "score_bands": {
            "likely_scam": sum(item["verdict"] == "Likely Scam" for item in results),
            "caution": sum(item["verdict"] == "Caution" for item in results),
            "likely_legitimate": sum(item["verdict"] == "Likely Legitimate" for item in results),
        },
        "rows": results,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path, help="Path to fake_job_postings.csv")
    parser.add_argument("--per-class", type=int, default=15, help="Rows sampled per label (default: 15)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic sampling seed")
    parser.add_argument("--live", action="store_true", help="Confirm use of live SerpApi searches")
    parser.add_argument("--output", type=Path, help="Optional JSON report path; no posting text is saved")
    parser.add_argument("--cache-db", type=Path, help="Optional isolated cache database for resuming a run")
    args = parser.parse_args()

    if not args.csv_file.is_file():
        parser.error(f"CSV file not found: {args.csv_file}")
    if args.per_class < 1:
        parser.error("--per-class must be at least 1")
    if not args.live:
        parser.error("Live searches can consume quota or incur charges; pass --live to confirm.")
    if not settings.serpapi_key or settings.serpapi_key.strip() in ("", "your_serpapi_key_here"):
        parser.error("A non-placeholder SERPAPI_KEY must be configured in the environment or .env.")

    try:
        sample = load_sample(args.csv_file, args.per_class, args.seed)
        report = asyncio.run(
            run_live_benchmark(sample, args.csv_file, args.seed, args.output, args.cache_db)
        )
    except Exception as exc:
        print(f"Benchmark failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report["metrics"], indent=2))
    print(f"Live searches: {report['search_counts']['live_requests']}")
    if args.output:
        print(f"Report saved to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())