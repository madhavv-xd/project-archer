"""Crypto helpers shared by the two auth systems.

- Dashboard auth: bcrypt password hashing + HS256 JWTs.
- LLM API auth: `arch_sk_` keys stored as SHA-256(key + API_KEY_SALT).
"""

import hashlib
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

API_KEY_PREFIX = "arch_sk_"
_ALPHABET = string.ascii_letters + string.digits


# --- Passwords -------------------------------------------------------------

def hash_password(password: str) -> str:
    # bcrypt operates on at most 72 bytes; truncate explicitly to stay in spec.
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))


# --- JWT (dashboard) -------------------------------------------------------

def create_access_token(user_id: uuid.UUID, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        return None


# --- API keys (LLM API) ----------------------------------------------------

def generate_api_key() -> str:
    body = "".join(secrets.choice(_ALPHABET) for _ in range(48))
    return f"{API_KEY_PREFIX}{body}"


def hash_api_key(key: str) -> str:
    return hashlib.sha256((key + settings.API_KEY_SALT).encode()).hexdigest()
