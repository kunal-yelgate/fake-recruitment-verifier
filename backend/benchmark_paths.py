"""Path validation helpers for local benchmark commands."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def resolve_benchmark_path(path: Path) -> Path:
    """Resolve a benchmark path and reject paths outside the repository."""
    resolved = path.expanduser().resolve()
    if not resolved.is_relative_to(REPOSITORY_ROOT):
        raise ValueError(f"Benchmark paths must stay inside {REPOSITORY_ROOT}.")
    return resolved
