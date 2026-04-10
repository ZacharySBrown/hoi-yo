"""Cloud authentication -- password + JWT cookies.

Uses bcrypt for password hashing and PyJWT for stateless session tokens.
Environment variables:
  HOIYO_PASSWORD_HASH  -- bcrypt hash of the shared password
  HOIYO_JWT_SECRET     -- random string used to sign JWTs
"""

from __future__ import annotations

import os
import time

import bcrypt
import jwt
from fastapi import HTTPException, Request

# ─── Configuration ────────────────────────────────────────────────────

COOKIE_NAME = "hoi_yo_token"
TOKEN_LIFETIME_SECONDS = 24 * 60 * 60  # 24 hours


def _get_password_hash() -> str:
    value = os.environ.get("HOIYO_PASSWORD_HASH", "")
    if not value:
        raise RuntimeError("HOIYO_PASSWORD_HASH environment variable is not set")
    return value


def _get_jwt_secret() -> str:
    value = os.environ.get("HOIYO_JWT_SECRET", "")
    if not value:
        raise RuntimeError("HOIYO_JWT_SECRET environment variable is not set")
    return value


# ─── Password Utilities ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Check *password* against a bcrypt *hashed* value."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ─── JWT Utilities ────────────────────────────────────────────────────

def create_token(secret: str) -> str:
    """Create a signed JWT with a 24-hour expiry."""
    payload = {
        "sub": "hoi-yo-user",
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str, secret: str) -> bool:
    """Return True if *token* is a valid, non-expired JWT."""
    try:
        jwt.decode(token, secret, algorithms=["HS256"])
        return True
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False


# ─── FastAPI Dependency ───────────────────────────────────────────────

async def auth_required(request: Request) -> bool:
    """FastAPI dependency -- raises 401 if the session cookie is missing/invalid."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    secret = _get_jwt_secret()
    if not verify_token(token, secret):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return True
