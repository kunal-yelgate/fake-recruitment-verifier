"""Contract tests for the privacy-safe benchmark fixture."""

import asyncio
import json
import re
from pathlib import Path

import pytest

from benchmark_synthetic_dataset import run_benchmark

DATASET = Path(__file__).resolve().parents[1] / "benchmarks" / "dataset"
POSTINGS = DATASET / "postings.json"
PROVENANCE = DATASET / "README.md"
ALLOWED_LABELS = {"scam", "legit", "ambiguous"}


def _load_postings() -> list[dict[str, str]]:
    with POSTINGS.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_benchmark_schema_count_and_label_balance() -> None:
    postings = _load_postings()

    assert len(postings) >= 100
    assert all(set(item) == {"id", "label", "text"} for item in postings)
    assert all(
        isinstance(item["id"], str)
        and isinstance(item["label"], str)
        and isinstance(item["text"], str)
        and item["id"].strip()
        and item["text"].strip()
        and item["label"] in ALLOWED_LABELS
        for item in postings
    )
    assert len({item["id"] for item in postings}) == len(postings)
    labels = {label: sum(item["label"] == label for item in postings) for label in ALLOWED_LABELS}
    assert all(count >= 20 for count in labels.values())


def test_benchmark_contains_required_patterns() -> None:
    text = "\n".join(item["text"].lower() for item in _load_postings())

    assert "whatsapp" in text
    assert "inr" in text or "₹" in text
    assert "fee" in text or "deposit" in text
    assert "urgent" in text
    assert "offer" in text


def test_benchmark_has_no_contact_pii_and_documents_provenance() -> None:
    text = "\n".join(item["text"] for item in _load_postings())

    # Synthetic fixtures must not accidentally turn into a contact database.
    assert not re.search(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", text, re.IGNORECASE)
    assert not re.search(r"(?<!\d)(?:\+?\d[\s-]?){8,}\d(?!\d)", text)
    assert not re.search(r"https?://|www\.", text, re.IGNORECASE)

    provenance = PROVENANCE.read_text(encoding="utf-8").lower()
    assert "synthetic" in provenance
    assert "no real contact details" in provenance
    assert "not copied" in provenance


def test_synthetic_benchmark_metrics_are_recorded_regression_baseline() -> None:
    report = asyncio.run(run_benchmark(POSTINGS))
    metrics = report["metrics"]

    assert metrics["sample_size"] == 102
    assert metrics["accuracy"] == pytest.approx(2 / 3)
    assert metrics["macro_f1"] == pytest.approx(5 / 9)
    assert metrics["confusion_matrix"]["rows"] == {
        "scam": {"scam": 34, "legit": 0, "ambiguous": 0},
        "legit": {"scam": 0, "legit": 0, "ambiguous": 34},
        "ambiguous": {"scam": 0, "legit": 0, "ambiguous": 34},
    }
