"""Shared retry utility for LLM provider stream steps."""
from __future__ import annotations

import random
import time

_DEFAULT_MAX_ATTEMPTS = 5
_DEFAULT_BASE_DELAY = 2.0
_DEFAULT_MAX_DELAY = 60.0


def with_retry(
    fn,
    retryable_exc: type | tuple,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    base_delay: float = _DEFAULT_BASE_DELAY,
    max_delay: float = _DEFAULT_MAX_DELAY,
):
    """Call *fn* up to *max_attempts* times, backing off exponentially on *retryable_exc*.

    Raises RuntimeError when all attempts are exhausted.
    Any exception that is not an instance of *retryable_exc* propagates immediately.
    """
    for attempt in range(max_attempts):
        try:
            return fn()
        except retryable_exc:
            if attempt == max_attempts - 1:
                raise RuntimeError(
                    f"Rate limit: max retries ({max_attempts}) exceeded"
                )
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
            time.sleep(delay)
    raise RuntimeError(f"Rate limit: max retries ({max_attempts}) exceeded")
