"""RateLimiter — in-memory sliding-window rate limiting per API key."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Optional

_WINDOW_SECONDS = 60.0


class RateLimiter:
    def __init__(self):
        self._requests: dict[str, list[float]] = {}
        self._blocked: dict[str, int] = {}
        self._lock = threading.Lock()

    def _prune(self, key_id: str, now_ts: float) -> None:
        cutoff = now_ts - _WINDOW_SECONDS
        self._requests[key_id] = [t for t in self._requests.get(key_id, []) if t >= cutoff]

    def check(self, key_id: str, rpm_limit: int) -> dict:
        now_ts = time.time()
        with self._lock:
            self._prune(key_id, now_ts)
            current = len(self._requests.get(key_id, []))
            if current >= rpm_limit:
                self._blocked[key_id] = self._blocked.get(key_id, 0) + 1
                allowed = False
            else:
                self._requests.setdefault(key_id, []).append(now_ts)
                current += 1
                allowed = True
            oldest = min(self._requests[key_id]) if self._requests.get(key_id) else now_ts
            reset_at = datetime.fromtimestamp(
                oldest + _WINDOW_SECONDS, tz=timezone.utc
            ).isoformat()
        return {"allowed": allowed, "current_rpm": current, "limit": rpm_limit, "reset_at": reset_at}

    def reset(self, key_id: str) -> None:
        with self._lock:
            self._requests.pop(key_id, None)
            self._blocked.pop(key_id, None)

    def get_stats(self, key_id: str) -> dict:
        now_ts = time.time()
        with self._lock:
            self._prune(key_id, now_ts)
            return {
                "key_id": key_id,
                "requests_last_minute": len(self._requests.get(key_id, [])),
                "blocked_count": self._blocked.get(key_id, 0),
            }


_instance: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _instance
    if _instance is None:
        _instance = RateLimiter()
    return _instance
