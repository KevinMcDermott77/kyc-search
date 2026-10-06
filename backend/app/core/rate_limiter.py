"""
In-process token-bucket rate limiter for the Companies House API.

CH allows 600 requests per 5 minutes; we cap ourselves at 500 to leave headroom.
The bucket also honours CH's own X-Ratelimit-Remaining / X-Ratelimit-Reset headers,
so if CH reports fewer remaining requests than we think we have, we trust CH.

The service runs as a single uvicorn process, so an in-process bucket shared by
the single CompaniesHouseClient instance is sufficient.
"""

import asyncio
import time

CH_CAPACITY = 500
CH_WINDOW = 300  # seconds
CH_REFILL_RATE = CH_CAPACITY / CH_WINDOW  # tokens per second


class TokenBucket:
    def __init__(
        self,
        capacity: int = CH_CAPACITY,
        refill_rate: float = CH_REFILL_RATE,
        clock=time.monotonic,
    ) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._clock = clock
        self._tokens = float(capacity)
        self._ts = clock()
        self._blocked_until = 0.0  # monotonic time before which no requests may go out
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        self._tokens = min(self.capacity, self._tokens + (now - self._ts) * self.refill_rate)
        self._ts = now

    async def acquire(self) -> None:
        """Block until a token is available, then take it."""
        async with self._lock:
            while True:
                now = self._clock()
                if now < self._blocked_until:
                    await asyncio.sleep(self._blocked_until - now)
                    continue
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                await asyncio.sleep((1 - self._tokens) / self.refill_rate)

    def update_from_headers(self, headers) -> None:
        """Reconcile with CH's view of the rate limit window."""
        remaining = headers.get("X-Ratelimit-Remaining")
        if remaining is None:
            return
        try:
            remaining_n = int(remaining)
        except ValueError:
            return
        self._refill()
        self._tokens = min(self._tokens, float(max(remaining_n, 0)))
        if remaining_n <= 0:
            self._blocked_until = self._clock() + seconds_until_reset(headers.get("X-Ratelimit-Reset"))


def seconds_until_reset(reset_header: str | None) -> float:
    """X-Ratelimit-Reset is a unix timestamp; fall back to a full window if absent/invalid."""
    if reset_header:
        try:
            return max(0.0, min(float(reset_header) - time.time(), CH_WINDOW))
        except ValueError:
            pass
    return float(CH_WINDOW)
