from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    """Simple in-memory rate limiter using a sliding window approach."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        self._requests[key] = [t for t in self._requests[key] if t > window_start]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True

    def get_retry_after(self, key: str) -> int | None:
        now = time.time()
        window_start = now - self.window_seconds
        recent = [t for t in self._requests.get(key, []) if t > window_start]

        if len(recent) < self.max_requests:
            return None

        oldest_in_window = min(recent)
        retry_after = int((oldest_in_window + self.window_seconds) - now) + 1
        return max(1, retry_after)


_auth_limiter = RateLimiter(max_requests=5, window_seconds=60)
_registration_limiter = RateLimiter(max_requests=3, window_seconds=300)


def check_rate_limiter(key: str, limiter: RateLimiter | None = None):
    if limiter is None:
        limiter = _auth_limiter
    if not limiter.is_allowed(key):
        retry_after = limiter.get_retry_after(key)
        raise RateLimitExceeded(retry_after=retry_after)


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int | None = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Try again in {retry_after} seconds.")
