"""Admin gate (require_admin) — the real 403 boundary. Pure/mocked, no DB."""

import pytest
from fastapi import HTTPException

from app.api.middleware.auth import require_admin
from app.db.models import User


async def test_require_admin_allows_admin():
    user = User(email="a@x.com", role="admin", is_active=True)
    assert await require_admin(user) is user


async def test_require_admin_rejects_regular_user():
    user = User(email="u@x.com", role="user", is_active=True)
    with pytest.raises(HTTPException) as exc:
        await require_admin(user)
    assert exc.value.status_code == 403
