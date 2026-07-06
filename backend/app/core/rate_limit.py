"""Redis-backed limits: per-key sliding-window RPM + per-user monthly quota.

Every Redis failure is caught and fails OPEN (request allowed, warning logged) —
availability over enforcement in 2A. When REDIS_URL is unset there is no client
at all and the enforce_limits dependency skips these checks entirely.
"""

import logging
import math
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger("archer.rate_limit")

WINDOW_SECONDS = 60
# Sorted-set keys expire well after the window so idle keys don't linger.
KEY_TTL_SECONDS = 120
# Monthly quota counters expire after ~35 days — outlives their month.
MONTH_TTL_SECONDS = 35 * 24 * 3600


@dataclass
class LimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int


class RateLimitExceeded(Exception):
    """Carries the OpenAI-style 429 payload; rendered by the handler in app.main."""

    def __init__(self, code: str, message: str, retry_after: int, headers: dict[str, str]):
        self.code = code
        self.message = message
        self.retry_after = retry_after
        self.headers = headers
        super().__init__(message)


def _now() -> float:
    return time.time()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _seconds_to_next_month(now: datetime) -> int:
    if now.month == 12:
        nxt = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        nxt = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return int((nxt - now).total_seconds())


async def check_rate_limit(redis, api_key_id, limit: int) -> LimitResult:
    """Sliding window over a sorted set rl:{api_key_id}, one pipeline round-trip."""
    key = f"rl:{api_key_id}"
    now = _now()
    try:
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
        pipe.zadd(key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
        pipe.zcard(key)
        pipe.zrange(key, 0, 0, withscores=True)
        pipe.expire(key, KEY_TTL_SECONDS)
        _, _, count, oldest, _ = await pipe.execute()
    except Exception:
        logger.warning("Redis error — rate limit check skipped (fail-open)", exc_info=True)
        return LimitResult(True, limit, limit, 0)

    if oldest:
        reset = max(1, math.ceil(oldest[0][1] + WINDOW_SECONDS - now))
    else:
        reset = 0
    return LimitResult(count <= limit, limit, max(0, limit - count), reset)


async def check_monthly_quota(redis, user_id, limit: int) -> LimitResult:
    """INCR on quota:{user_id}:{YYYY-MM} (UTC calendar month, counts requests)."""
    now = _utcnow()
    key = f"quota:{user_id}:{now.strftime('%Y-%m')}"
    try:
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, MONTH_TTL_SECONDS)
        count, _ = await pipe.execute()
    except Exception:
        logger.warning("Redis error — quota check skipped (fail-open)", exc_info=True)
        return LimitResult(True, limit, limit, 0)

    return LimitResult(count <= limit, limit, max(0, limit - count), _seconds_to_next_month(now))
