"""Rate limiter + quota checks (fakeredis) and the enforce_limits dependency.

429s never reach the route body (enforce_limits raises first), so no
request_logs row can be written for a rejected request — asserted here by the
dependency raising before returning.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fakeredis import aioredis as fakeredis
from fastapi import Response
from starlette.requests import Request

from app.api.middleware.auth import enforce_limits
from app.core import rate_limit
from app.core.rate_limit import (
    RateLimitExceeded,
    check_monthly_quota,
    check_rate_limit,
)
from app.db.models import ApiKey, User

KEY_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=True)


class ExplodingRedis:
    def pipeline(self):
        raise ConnectionError("redis down")


# --- sliding window -----------------------------------------------------------


async def test_limit_allows_up_to_rpm_and_rejects_next(redis):
    for i in range(30):
        result = await check_rate_limit(redis, KEY_ID, 30)
        assert result.allowed, f"request {i + 1} should be allowed"
    result = await check_rate_limit(redis, KEY_ID, 30)
    assert result.allowed is False
    assert result.remaining == 0
    assert result.reset_seconds >= 1


async def test_window_slides(redis, monkeypatch):
    t = 1_000_000.0
    monkeypatch.setattr(rate_limit, "_now", lambda: t)
    for _ in range(30):
        await check_rate_limit(redis, KEY_ID, 30)
    assert (await check_rate_limit(redis, KEY_ID, 30)).allowed is False

    # 61 seconds later the old entries are outside the window.
    monkeypatch.setattr(rate_limit, "_now", lambda: t + 61)
    assert (await check_rate_limit(redis, KEY_ID, 30)).allowed is True


async def test_remaining_counts_down(redis):
    first = await check_rate_limit(redis, KEY_ID, 30)
    second = await check_rate_limit(redis, KEY_ID, 30)
    assert first.remaining == 29
    assert second.remaining == 28


async def test_rate_limit_fails_open_on_redis_error():
    result = await check_rate_limit(ExplodingRedis(), KEY_ID, 30)
    assert result.allowed is True


# --- monthly quota -------------------------------------------------------------


async def test_quota_rejects_after_limit(redis):
    for _ in range(5):
        result = await check_monthly_quota(redis, USER_ID, 5)
        assert result.allowed
    result = await check_monthly_quota(redis, USER_ID, 5)
    assert result.allowed is False
    assert result.remaining == 0


async def test_quota_rolls_over_on_new_month(redis, monkeypatch):
    monkeypatch.setattr(
        rate_limit, "_utcnow", lambda: datetime(2026, 7, 15, tzinfo=timezone.utc)
    )
    for _ in range(3):
        await check_monthly_quota(redis, USER_ID, 3)
    assert (await check_monthly_quota(redis, USER_ID, 3)).allowed is False

    monkeypatch.setattr(
        rate_limit, "_utcnow", lambda: datetime(2026, 8, 1, tzinfo=timezone.utc)
    )
    assert (await check_monthly_quota(redis, USER_ID, 3)).allowed is True


async def test_quota_fails_open_on_redis_error():
    result = await check_monthly_quota(ExplodingRedis(), USER_ID, 5)
    assert result.allowed is True


# --- enforce_limits dependency -------------------------------------------------


def _request_with(redis):
    class App:
        pass

    app = App()
    app.state = App()
    app.state.redis = redis
    return Request({"type": "http", "app": app, "headers": []})


def _api_key():
    return ApiKey(id=KEY_ID, user_id=USER_ID, user=User(plan="free"), is_active=True)


async def test_enforce_limits_sets_headers_on_success(redis):
    # RATE_LIMIT_RPM defaults to 30.
    request = _request_with(redis)
    response = Response()

    returned = await enforce_limits(request, response, _api_key())

    assert returned.id == KEY_ID
    assert response.headers["X-RateLimit-Limit-Requests"] == "30"
    assert response.headers["X-RateLimit-Remaining-Requests"] == "29"
    assert int(response.headers["X-RateLimit-Reset-Requests"]) >= 1
    assert request.state.rate_limit_headers["X-RateLimit-Limit-Requests"] == "30"


async def test_enforce_limits_raises_429_shape_when_limited(redis):
    request = _request_with(redis)
    for _ in range(30):
        await enforce_limits(request, Response(), _api_key())

    with pytest.raises(RateLimitExceeded) as exc_info:
        await enforce_limits(request, Response(), _api_key())

    exc = exc_info.value
    assert exc.code == "rate_limit_exceeded"
    assert exc.retry_after >= 1
    assert exc.headers["X-RateLimit-Remaining-Requests"] == "0"


async def test_enforce_limits_quota_code(redis, monkeypatch):
    from app.api.middleware import auth as auth_module

    monkeypatch.setattr(
        auth_module.settings,
        "MONTHLY_QUOTA_REQUESTS",
        1,
        raising=False,
    )
    request = _request_with(redis)
    await enforce_limits(request, Response(), _api_key())

    with pytest.raises(RateLimitExceeded) as exc_info:
        await enforce_limits(request, Response(), _api_key())
    assert exc_info.value.code == "monthly_quota_exceeded"


async def test_enforce_limits_noop_without_redis():
    request = _request_with(None)
    response = Response()
    returned = await enforce_limits(request, response, _api_key())
    assert returned.id == KEY_ID
    assert "X-RateLimit-Limit-Requests" not in response.headers
