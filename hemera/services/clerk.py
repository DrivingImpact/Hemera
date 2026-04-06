"""Clerk JWT verification and user extraction."""

import jwt
import httpx
from dataclasses import dataclass
from functools import lru_cache
from hemera.config import get_settings


@dataclass
class ClerkUser:
    clerk_id: str
    email: str
    org_name: str
    role: str


@lru_cache(maxsize=1)
def _fetch_jwks() -> bytes:
    settings = get_settings()
    if not settings.clerk_secret_key:
        return b""
    jwks_url = settings.clerk_jwks_url
    if not jwks_url:
        return b""
    response = httpx.get(jwks_url, timeout=10)
    response.raise_for_status()
    return response.content


def _get_clerk_public_key() -> bytes:
    return _fetch_jwks()


def verify_clerk_token(token: str) -> ClerkUser | None:
    try:
        public_key = _get_clerk_public_key()
        if not public_key:
            return None
        payload = jwt.decode(token, public_key, algorithms=["RS256"], options={"verify_aud": False})
        metadata = payload.get("public_metadata", {})
        return ClerkUser(
            clerk_id=payload.get("sub", ""),
            email=payload.get("email", ""),
            org_name=metadata.get("org_name", ""),
            role=metadata.get("role", "client"),
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None
