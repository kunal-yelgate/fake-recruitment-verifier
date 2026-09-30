"""Small dependency-free metrics registry for operational counters."""

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Metrics:
    cache_hits: int = 0
    cache_misses: int = 0
    serpapi_requests: int = 0
    serpapi_errors: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def increment(self, name: str) -> None:
        with self._lock:
            setattr(self, name, getattr(self, name) + 1)

    def prometheus(self) -> str:
        with self._lock:
            values = {
                "truerecruit_cache_hits_total": self.cache_hits,
                "truerecruit_cache_misses_total": self.cache_misses,
                "truerecruit_serpapi_requests_total": self.serpapi_requests,
                "truerecruit_serpapi_errors_total": self.serpapi_errors,
            }
        return "".join(
            f"# TYPE {name} counter\n{name} {value}\n"
            for name, value in values.items()
        )


metrics = Metrics()
