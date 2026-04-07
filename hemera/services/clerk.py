"""Clerk JWT verification and user extraction."""

import jwt
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
def _get_jwks_client() -> jwt.PyJWKClient | None:
    settings = get_settings()
    jwks_url = settings.clerk_jwks_url
    if not jwks_url:
        return None
    return jwt.PyJWKClient(jwks_url)


def verify_clerk_token(token: str) -> ClerkUser | None:
    try:
        client = _get_jwks_client()
        if not client:
            return None
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
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
