"""Path validation helpers for local benchmark commands."""

import json
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def resolve_benchmark_path(path: Path) -> Path:
    """Resolve a benchmark path and reject paths outside the repository."""
    resolved = path.expanduser().resolve()
    if not resolved.is_relative_to(REPOSITORY_ROOT):
        raise ValueError(f"Benchmark paths must stay inside {REPOSITORY_ROOT}.")
    return resolved


def ensure_benchmark_parent(path: Path) -> Path:
    """Resolve a benchmark path and create its repository-confined parent."""
    resolved = resolve_benchmark_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)  # NOSONAR -- resolved paths stay under REPOSITORY_ROOT.
    return resolved


def write_benchmark_report(path: Path, report: dict[str, Any]) -> None:
    """Write a JSON report only to a path inside the repository."""
    resolved = ensure_benchmark_parent(path)
    resolved.write_text(  # NOSONAR -- resolved paths stay under REPOSITORY_ROOT.
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
