"""Small dependency-free metrics registry for operational counters."""

from dataclasses import dataclass, field
from threading import Lock

from app.config import settings


@dataclass
class Metrics:
    cache_hits: int = 0
    cache_misses: int = 0
    serpapi_requests: int = 0
    serpapi_errors: int = 0
    serpapi_quota_used: int = 0
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
                "truerecruit_serpapi_quota_used_total": self.serpapi_quota_used,
            }
            cache_total = self.cache_hits + self.cache_misses
            hit_rate = self.cache_hits / cache_total if cache_total else 0.0
            quota_limit = settings.serpapi_quota_limit
        output = "".join(f"# TYPE {name} counter\n{name} {value}\n" for name, value in values.items())
        output += "# TYPE truerecruit_cache_hit_rate gauge\n"
        output += f"truerecruit_cache_hit_rate {hit_rate:.6f}\n"
        if quota_limit is not None:
            output += "# TYPE truerecruit_serpapi_quota_limit gauge\n"
            output += f"truerecruit_serpapi_quota_limit {quota_limit}\n"
            output += "# TYPE truerecruit_serpapi_quota_remaining gauge\n"
            output += f"truerecruit_serpapi_quota_remaining {max(quota_limit - values['truerecruit_serpapi_quota_used_total'], 0)}\n"
        return output


metrics = Metrics()
