"""Admin PIN checking and in-memory failure rate limiting."""
import hmac
import time
from collections import deque

_DEFAULT_LIMITER = None


def limiter():
    """Return the process-wide failure limiter, created lazily on first use."""
    global _DEFAULT_LIMITER
    if _DEFAULT_LIMITER is None:
        _DEFAULT_LIMITER = FailureLimiter(max_failures=5, window_seconds=60)
    return _DEFAULT_LIMITER


def pin_ok(app_config: dict, provided: str) -> bool:
    """True when the provided PIN matches (constant-time); True if no PIN is set."""
    expected = app_config.get("ADMIN_PIN") or ""
    if not expected:
        return True
    return hmac.compare_digest(provided, expected)


class FailureLimiter:
    """Block a key after `max_failures` failures within `window_seconds`.

    Keys are client IPs. The time source is an injectable zero-argument
    callable (`now`) so tests can advance a fake clock.
    """

    def __init__(self, max_failures: int = 5, window_seconds: float = 60, now=None):
        """Store settings; `now` defaults to time.monotonic."""
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._now = now if now is not None else time.monotonic
        self._failures: dict = {}

    def blocked(self, key: str) -> bool:
        """True when the key has >= max_failures failures still inside the window."""
        self._prune(key, self._now())
        return len(self._failures.get(key, ())) >= self.max_failures

    def record(self, key: str) -> None:
        """Record a failure for the key (also prunes aged-out entries)."""
        self._prune(key, self._now())
        self._failures.setdefault(key, deque()).append(self._now())

    def reset(self, key: str) -> None:
        """Forget all recorded failures for the key (tests)."""
        self._failures.pop(key, None)

    def _prune(self, key: str, t: float) -> None:
        """Drop the key's failures that have aged out of the window."""
        entries = self._failures.get(key)
        if not entries:
            return
        cutoff = t - self.window_seconds
        while entries and entries[0] < cutoff:
            entries.popleft()
        if not entries:
            self._failures.pop(key, None)
