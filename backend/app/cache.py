"""SQLite-based 24h query cache to save SerpApi credits."""

import hashlib
import json
import sqlite3
import time
from typing import Any

from app.config import settings
from app.metrics import metrics


class QueryCache:
    def __init__(self, db_path: str = settings.cache_db_path, ttl_hours: int = settings.cache_ttl_hours):
        self.db_path = db_path
        self.ttl_seconds = ttl_hours * 3600
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS serpapi_cache (
                    cache_key TEXT PRIMARY KEY,
                    engine TEXT,
                    query TEXT,
                    response_json TEXT,
                    created_at REAL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_created ON serpapi_cache(created_at)")
            conn.commit()

    @staticmethod
    def compute_key(engine: str, params: dict[str, Any]) -> str:
        """Deterministically hash the engine and query parameters."""
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        raw = f"{engine}:{sorted_params}".encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, engine: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Retrieve cached response if within TTL, else return None."""
        key = self.compute_key(engine, params)
        now = time.time()
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT response_json, created_at FROM serpapi_cache WHERE cache_key = ?",
                    (key,),
                )
                row = cur.fetchone()
                if row:
                    response_json, created_at = row["response_json"], row["created_at"]
                    if (now - created_at) <= self.ttl_seconds:
                        metrics.increment("cache_hits")
                        return json.loads(response_json)
                    else:
                        # Expired: delete record
                        conn.execute("DELETE FROM serpapi_cache WHERE cache_key = ?", (key,))
                        conn.commit()
        except Exception:
            metrics.increment("cache_misses")
            return None
        metrics.increment("cache_misses")
        return None

    def set(self, engine: str, params: dict[str, Any], data: dict[str, Any]) -> None:
        """Save a SerpApi response with current timestamp."""
        if data.get("_source") in {"mock", "error"} or data.get("_api_error") or data.get("_is_mock"):
            return
        key = self.compute_key(engine, params)
        now = time.time()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO serpapi_cache
                    (cache_key, engine, query, response_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        engine,
                        str(params.get("q", params.get("query", ""))),
                        json.dumps(data),
                        now,
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all cached queries."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM serpapi_cache")
                conn.commit()
        except Exception:
            pass

    def get_stats(self) -> dict[str, Any]:
        """Return cache health metrics."""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) as total FROM serpapi_cache")
                total = cur.fetchone()["total"]
                return {"total_cached_queries": total, "ttl_hours": settings.cache_ttl_hours}
        except Exception as e:
            return {"total_cached_queries": 0, "error": str(e)}


# Global cache instance
cache = QueryCache()
