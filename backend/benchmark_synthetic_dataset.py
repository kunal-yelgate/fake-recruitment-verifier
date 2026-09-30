"""Offline metrics for the checked-in synthetic benchmark corpus.

This benchmark intentionally evaluates only the deterministic in-posting
threat signal. It never calls SerpApi or any other provider.
"""

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.models import ExtractedFields
from app.scoring import calculate_risk_score
from app.signals.text_threats import check_in_text_threats

LABELS = ("scam", "legit", "ambiguous")
DATASET_PATH = Path(__file__).resolve().parent / "benchmarks" / "dataset" / "postings.json"


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, str]]:
    """Load and validate the privacy-safe benchmark fixture."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Benchmark dataset must be a non-empty JSON list.")
    for row in rows:
        if set(row) != {"id", "label", "text"} or row["label"] not in LABELS:
            raise ValueError(f"Invalid benchmark row: {row!r}")
    return rows


def _predicted_label(verdict: str) -> str:
    return {
        "Likely Scam": "scam",
        "Caution": "ambiguous",
        "Likely Legitimate": "legit",
    }[verdict]


def calculate_metrics(results: list[dict[str, str]]) -> dict[str, Any]:
    """Return multiclass precision, recall, F1, and a row=true matrix."""
    matrix = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    for result in results:
        matrix[result["label"]][result["predicted_label"]] += 1

    per_class: dict[str, dict[str, float | int]] = {}
    for label in LABELS:
        true_positive = matrix[label][label]
        predicted_total = sum(matrix[actual][label] for actual in LABELS)
        actual_total = sum(matrix[label].values())
        precision = true_positive / predicted_total if predicted_total else 0.0
        recall = true_positive / actual_total if actual_total else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        per_class[label] = {
            "support": actual_total,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    accuracy = sum(matrix[label][label] for label in LABELS) / len(results) if results else 0.0
    return {
        "sample_size": len(results),
        "accuracy": accuracy,
        "macro_precision": sum(item["precision"] for item in per_class.values()) / len(LABELS),
        "macro_recall": sum(item["recall"] for item in per_class.values()) / len(LABELS),
        "macro_f1": sum(item["f1"] for item in per_class.values()) / len(LABELS),
        "per_class": per_class,
        "confusion_matrix": {"labels": list(LABELS), "rows": matrix},
    }


async def run_benchmark(path: Path = DATASET_PATH) -> dict[str, Any]:
    """Score every synthetic posting offline and return its metrics."""
    rows = load_dataset(path)
    results = []
    for row in rows:
        signal = await check_in_text_threats(ExtractedFields(), row["text"])
        _, verdict, _, _ = calculate_risk_score([signal])
        results.append(
            {
                "id": row["id"],
                "label": row["label"],
                "predicted_label": _predicted_label(verdict),
            }
        )
    return {"dataset": str(path), "metrics": calculate_metrics(results), "rows": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    report = asyncio.run(run_benchmark(args.dataset))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
