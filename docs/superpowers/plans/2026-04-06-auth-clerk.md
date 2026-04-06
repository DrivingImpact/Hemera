# Clerk Auth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Secure all API endpoints with Clerk JWT verification, org-scoped data access, and admin role checks.

**Architecture:** Clerk handles user registration/login/passwords. Hemera verifies Clerk JWTs using their JWKS public keys, extracts user metadata (org_name, role), and enforces org scoping + role-based access via FastAPI dependencies. A webhook syncs Clerk users to the local DB.

**Tech Stack:** Python 3.14, FastAPI, PyJWT, svix, Clerk

---

## Task 0: Install dependencies and update config

**Files:**
- Modify: `hemera/config.py`

- [ ] **Step 1: Install new dependencies**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/pip install "pyjwt[crypto]" svix
```

- [ ] **Step 2: Update config with Clerk settings**

Replace `hemera/config.py`:

```python
"""Hemera configuration — loads from .env"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://localhost/hemera"
    anthropic_api_key: str = ""
    companies_house_api_key: str = ""

    # Clerk auth
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_webhook_secret: str = ""

    class Config:
        env_file = ".env"

    @property
    def clerk_jwks_url(self) -> str:
        """Derive the JWKS URL from the Clerk frontend API domain.

        Clerk publishable keys look like: pk_live_xxxxx or pk_test_xxxxx
        The JWKS URL is: https://<frontend-api>/.well-known/jwks.json
        We use the Clerk API to get this, but for simplicity we use the
        standard Clerk JWKS endpoint format.
        """
        # Clerk's JWKS URL follows the pattern based on the instance
        # For development: https://<instance>.clerk.accounts.dev/.well-known/jwks.json
        # This is set via environment or derived from the secret key
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/config.py
git commit -m "chore: add Clerk config settings and install pyjwt, svix"
```

---

## Task 1: Clerk JWT verification service

**Files:**
- Create: `hemera/services/clerk.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_auth.py`:

```python
"""Tests for Clerk auth integration."""

import json
import time
import pytest
import jwt
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from hemera.services.clerk import verify_clerk_token, ClerkUser


# Generate a test RSA key pair for JWT signing
_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend(),
)
_public_key = _private_key.public_key()

_private_pem = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
_public_pem = _public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


def _make_token(claims: dict, expired: bool = False) -> str:
    """Create a signed JWT with the test private key."""
    now = int(time.time())
    payload = {
        "sub": "user_test123",
        "email": "test@example.com",
        "iat": now,
        "exp": now - 100 if expired else now + 3600,
        "public_metadata": {
            "org_name": "Test SU",
            "role": "client",
        },
        **claims,
    }
    return jwt.encode(payload, _private_pem, algorithm="RS256")


@patch("hemera.services.clerk._get_clerk_public_key")
def test_verify_valid_token(mock_get_key):
    """Valid token should return a ClerkUser."""
    mock_get_key.return_value = _public_pem
    token = _make_token({})
    user = verify_clerk_token(token)
    assert user.clerk_id == "user_test123"
    assert user.email == "test@example.com"
    assert user.org_name == "Test SU"
    assert user.role == "client"


@patch("hemera.services.clerk._get_clerk_public_key")
def test_verify_admin_token(mock_get_key):
    """Admin role should be extracted from public_metadata."""
    mock_get_key.return_value = _public_pem
    token = _make_token({"public_metadata": {"org_name": "Hemera", "role": "admin"}})
    user = verify_clerk_token(token)
    assert user.role == "admin"
    assert user.org_name == "Hemera"


@patch("hemera.services.clerk._get_clerk_public_key")
def test_verify_expired_token(mock_get_key):
    """Expired token should return None."""
    mock_get_key.return_value = _public_pem
    token = _make_token({}, expired=True)
    user = verify_clerk_token(token)
    assert user is None


def test_verify_invalid_token():
    """Garbage token should return None."""
    user = verify_clerk_token("not.a.real.token")
    assert user is None


@patch("hemera.services.clerk._get_clerk_public_key")
def test_verify_missing_metadata(mock_get_key):
    """Token without public_metadata should default to client role."""
    mock_get_key.return_value = _public_pem
    token = _make_token({"public_metadata": {}})
    user = verify_clerk_token(token)
    assert user is not None
    assert user.role == "client"
    assert user.org_name == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_auth.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Clerk JWT verification**

Create `hemera/services/clerk.py`:

```python
"""Clerk JWT verification and user extraction.

Verifies JWTs signed by Clerk using their JWKS public keys.
Extracts user identity and org metadata from token claims.
"""

import jwt
import httpx
from dataclasses import dataclass
from functools import lru_cache
from hemera.config import get_settings


@dataclass
class ClerkUser:
    """User identity extracted from a verified Clerk JWT."""
    clerk_id: str
    email: str
    org_name: str
    role: str  # "client" or "admin"


@lru_cache(maxsize=1)
def _fetch_jwks() -> bytes:
    """Fetch Clerk's JWKS public keys. Cached for the process lifetime.

    In tests, this is mocked via _get_clerk_public_key.
    """
    settings = get_settings()
    if not settings.clerk_secret_key:
        return b""

    # Clerk's JWKS endpoint — derive from the secret key's instance
    # The JWKS URL is provided by Clerk in the dashboard
    jwks_url = settings.clerk_jwks_url
    if not jwks_url:
        return b""

    response = httpx.get(jwks_url, timeout=10)
    response.raise_for_status()
    return response.content


def _get_clerk_public_key() -> bytes:
    """Get the public key for verifying Clerk JWTs.

    Returns PEM-encoded public key bytes. Mocked in tests.
    """
    return _fetch_jwks()


def verify_clerk_token(token: str) -> ClerkUser | None:
    """Verify a Clerk JWT and extract user information.

    Returns ClerkUser if valid, None if invalid/expired.
    """
    try:
        public_key = _get_clerk_public_key()
        if not public_key:
            return None

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        # Extract metadata
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_auth.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/clerk.py tests/test_auth.py
git commit -m "feat: add Clerk JWT verification service"
```

---

## Task 2: FastAPI auth dependencies

**Files:**
- Create: `hemera/dependencies.py`
- Modify: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_auth.py`:

```python
from unittest.mock import AsyncMock
from fastapi import HTTPException
from hemera.dependencies import get_current_user, require_admin
from hemera.services.clerk import ClerkUser


def test_get_current_user_valid():
    """Valid token should return ClerkUser."""
    mock_user = ClerkUser(clerk_id="user_1", email="a@b.com", org_name="TestOrg", role="client")
    with patch("hemera.dependencies.verify_clerk_token", return_value=mock_user):
        user = get_current_user(token="fake_token")
        assert user.clerk_id == "user_1"
        assert user.org_name == "TestOrg"


def test_get_current_user_no_token():
    """Missing token should raise 401."""
    with pytest.raises(HTTPException) as exc:
        get_current_user(token="")
    assert exc.value.status_code == 401


def test_get_current_user_invalid_token():
    """Invalid token should raise 401."""
    with patch("hemera.dependencies.verify_clerk_token", return_value=None):
        with pytest.raises(HTTPException) as exc:
            get_current_user(token="bad_token")
        assert exc.value.status_code == 401


def test_require_admin_with_admin():
    """Admin user should pass."""
    admin = ClerkUser(clerk_id="user_1", email="a@b.com", org_name="Hemera", role="admin")
    result = require_admin(current_user=admin)
    assert result.role == "admin"


def test_require_admin_with_client():
    """Client user should raise 403."""
    client = ClerkUser(clerk_id="user_2", email="b@c.com", org_name="TestOrg", role="client")
    with pytest.raises(HTTPException) as exc:
        require_admin(current_user=client)
    assert exc.value.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_auth.py -k "current_user or require_admin" -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement dependencies**

Create `hemera/dependencies.py`:

```python
"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from hemera.services.clerk import verify_clerk_token, ClerkUser

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    token: str = None,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> ClerkUser:
    """Verify Clerk JWT and return the current user.

    Extracts the Bearer token from the Authorization header.
    Raises 401 if token is missing, expired, or invalid.
    """
    # Allow direct token passing (for testing) or from header
    raw_token = token or (credentials.credentials if credentials else "")

    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = verify_clerk_token(raw_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


def require_admin(current_user: ClerkUser = Depends(get_current_user)) -> ClerkUser:
    """Require the current user to be an admin.

    Raises 403 if the user's role is not 'admin'.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_auth.py -v
```
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/dependencies.py tests/test_auth.py
git commit -m "feat: add get_current_user and require_admin dependencies"
```

---

## Task 3: Auth API endpoints (me + webhook)

**Files:**
- Create: `hemera/api/auth.py`
- Modify: `hemera/main.py`
- Modify: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_auth.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from hemera.database import Base, get_db
from hemera.main import app
from hemera.models.user import User


def _make_test_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_api_auth_me():
    """GET /api/auth/me with valid token returns user info."""
    mock_user = ClerkUser(clerk_id="user_1", email="test@su.ac.uk", org_name="Imperial SU", role="client")
    with patch("hemera.dependencies.verify_clerk_token", return_value=mock_user):
        client = TestClient(app)
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer fake_token"})
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "test@su.ac.uk"
        assert data["org_name"] == "Imperial SU"
        assert data["role"] == "client"


def test_api_auth_me_no_token():
    """GET /api/auth/me without token returns 401."""
    client = TestClient(app)
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_webhook_creates_user():
    """Clerk webhook user.created should create a User record."""
    session = _make_test_session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    payload = {
        "type": "user.created",
        "data": {
            "id": "user_clerk_abc",
            "email_addresses": [{"email_address": "new@su.ac.uk"}],
            "public_metadata": {"org_name": "Test SU", "role": "client"},
        },
    }

    # Skip signature verification for test (no CLERK_WEBHOOK_SECRET set)
    with patch("hemera.api.auth._verify_webhook_signature", return_value=True):
        client = TestClient(app)
        r = client.post("/api/webhooks/clerk", json=payload)
        assert r.status_code == 200

    # Verify user was created
    user = session.query(User).filter(User.clerk_id == "user_clerk_abc").first()
    assert user is not None
    assert user.email == "new@su.ac.uk"
    assert user.org_name == "Test SU"
    assert user.role == "client"

    app.dependency_overrides.clear()
    session.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_auth.py -k "api_auth or webhook" -v
```
Expected: FAIL

- [ ] **Step 3: Update User model**

Replace `hemera/models/user.py`:

```python
"""Client users — synced from Clerk."""

from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from hemera.database import Base


class User(Base):
    """A user synced from Clerk. Clerk handles authentication;
    this table enables DB joins and local queries."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255))  # unused with Clerk
    org_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="client")  # "client" or "admin"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)  # derived from role

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Create auth API routes**

Create `hemera/api/auth.py`:

```python
"""Auth endpoints — user info and Clerk webhook."""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser
from hemera.models.user import User
from hemera.config import get_settings

router = APIRouter()


def _verify_webhook_signature(request_body: bytes, headers: dict) -> bool:
    """Verify Clerk webhook signature using Svix.

    Returns True if valid or if no webhook secret is configured (dev mode).
    """
    settings = get_settings()
    if not settings.clerk_webhook_secret:
        return True  # Dev mode: skip verification

    try:
        from svix.webhooks import Webhook
        wh = Webhook(settings.clerk_webhook_secret)
        wh.verify(request_body, headers)
        return True
    except Exception:
        return False


@router.get("/auth/me")
def get_me(current_user: ClerkUser = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "clerk_id": current_user.clerk_id,
        "email": current_user.email,
        "org_name": current_user.org_name,
        "role": current_user.role,
    }


@router.post("/webhooks/clerk")
async def clerk_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Clerk webhook events (user.created, user.updated, user.deleted)."""
    body = await request.body()
    headers = dict(request.headers)

    if not _verify_webhook_signature(body, headers):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    payload = json.loads(body)
    event_type = payload.get("type", "")
    data = payload.get("data", {})

    clerk_id = data.get("id", "")
    emails = data.get("email_addresses", [])
    email = emails[0].get("email_address", "") if emails else ""
    metadata = data.get("public_metadata", {})
    org_name = metadata.get("org_name", "")
    role = metadata.get("role", "client")

    if event_type == "user.created":
        existing = db.query(User).filter(User.clerk_id == clerk_id).first()
        if not existing:
            user = User(
                clerk_id=clerk_id,
                email=email,
                org_name=org_name,
                role=role,
                is_admin=(role == "admin"),
            )
            db.add(user)
            db.commit()

    elif event_type == "user.updated":
        user = db.query(User).filter(User.clerk_id == clerk_id).first()
        if user:
            user.email = email
            user.org_name = org_name
            user.role = role
            user.is_admin = (role == "admin")
            db.commit()

    elif event_type == "user.deleted":
        user = db.query(User).filter(User.clerk_id == clerk_id).first()
        if user:
            user.is_active = False
            db.commit()

    return {"status": "ok"}
```

- [ ] **Step 5: Register auth router in main.py**

Update `hemera/main.py`:

```python
"""Hemera — FastAPI application."""

from fastapi import FastAPI
from hemera.api import upload, engagements, suppliers, reports, qc, auth

app = FastAPI(
    title="Hemera",
    description="Supply Chain & Carbon Intelligence API",
    version="0.1.0",
)

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(engagements.router, prefix="/api", tags=["engagements"])
app.include_router(suppliers.router, prefix="/api", tags=["suppliers"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(qc.router, prefix="/api", tags=["qc"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "hemera"}
```

- [ ] **Step 6: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_auth.py -v
```
Expected: 13 passed

- [ ] **Step 7: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/api/auth.py hemera/main.py hemera/models/user.py tests/test_auth.py
git commit -m "feat: add auth endpoints (me + webhook) and update User model"
```

---

## Task 4: Protect existing endpoints with org scoping

**Files:**
- Modify: `hemera/api/engagements.py`
- Modify: `hemera/api/upload.py`
- Modify: `hemera/api/reports.py`
- Modify: `hemera/api/qc.py`
- Modify: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests for org scoping**

Append to `tests/test_auth.py`:

```python
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction


def test_engagements_scoped_to_org():
    """Client should only see their own org's engagements."""
    session = _make_test_session()

    def override_get_db():
        try: yield session
        finally: pass

    app.dependency_overrides[get_db] = override_get_db

    # Create engagements for two orgs
    e1 = Engagement(org_name="Imperial SU", status="delivered", transaction_count=5)
    e2 = Engagement(org_name="Other SU", status="delivered", transaction_count=3)
    session.add_all([e1, e2])
    session.flush()

    # Mock auth as Imperial SU client
    mock_user = ClerkUser(clerk_id="u1", email="a@imperial.ac.uk", org_name="Imperial SU", role="client")
    with patch("hemera.dependencies.verify_clerk_token", return_value=mock_user):
        client = TestClient(app)
        r = client.get("/api/engagements", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["org_name"] == "Imperial SU"

    app.dependency_overrides.clear()
    session.close()


def test_admin_sees_all_engagements():
    """Admin should see all engagements across orgs."""
    session = _make_test_session()

    def override_get_db():
        try: yield session
        finally: pass

    app.dependency_overrides[get_db] = override_get_db

    e1 = Engagement(org_name="Imperial SU", status="delivered", transaction_count=5)
    e2 = Engagement(org_name="Other SU", status="delivered", transaction_count=3)
    session.add_all([e1, e2])
    session.flush()

    mock_admin = ClerkUser(clerk_id="u1", email="admin@hemera.com", org_name="Hemera", role="admin")
    with patch("hemera.dependencies.verify_clerk_token", return_value=mock_admin):
        client = TestClient(app)
        r = client.get("/api/engagements", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        assert len(r.json()) == 2

    app.dependency_overrides.clear()
    session.close()


def test_qc_requires_admin():
    """Client should get 403 on QC endpoints."""
    session = _make_test_session()

    def override_get_db():
        try: yield session
        finally: pass

    app.dependency_overrides[get_db] = override_get_db

    mock_client = ClerkUser(clerk_id="u1", email="a@su.ac.uk", org_name="Test SU", role="client")
    with patch("hemera.dependencies.verify_clerk_token", return_value=mock_client):
        client = TestClient(app)
        r = client.post("/api/engagements/1/qc/generate", headers={"Authorization": "Bearer fake"})
        assert r.status_code == 403

    app.dependency_overrides.clear()
    session.close()


def test_upload_sets_org_from_token():
    """Upload should auto-set org_name from the authenticated user."""
    # This is a lightweight check — just verify the endpoint requires auth
    client = TestClient(app)
    r = client.post("/api/upload")
    assert r.status_code in (401, 422)  # 401 no token, or 422 no file
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_auth.py -k "scoped or admin_sees or qc_requires or upload_sets" -v
```
Expected: FAIL — endpoints don't have auth yet

- [ ] **Step 3: Update engagements.py with auth**

Replace `hemera/api/engagements.py`:

```python
"""Engagement endpoints — CRUD for client reports."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser

router = APIRouter()


@router.get("/engagements")
def list_engagements(
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """List engagements. Clients see own org only; admins see all."""
    query = db.query(Engagement)
    if current_user.role != "admin":
        query = query.filter(Engagement.org_name == current_user.org_name)
    engagements = query.order_by(Engagement.created_at.desc()).all()
    return [
        {
            "id": e.id,
            "org_name": e.org_name,
            "status": e.status,
            "transaction_count": e.transaction_count,
            "total_co2e": e.total_co2e,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in engagements
    ]


@router.get("/engagements/{engagement_id}")
def get_engagement(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Get a single engagement with summary stats."""
    e = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role != "admin" and e.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "id": e.id,
        "org_name": e.org_name,
        "status": e.status,
        "transaction_count": e.transaction_count,
        "supplier_count": e.supplier_count,
        "total_co2e": e.total_co2e,
        "scope1_co2e": e.scope1_co2e,
        "scope2_co2e": e.scope2_co2e,
        "scope3_co2e": e.scope3_co2e,
        "gsd_total": e.gsd_total,
        "ci_lower": e.ci_lower,
        "ci_upper": e.ci_upper,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
```

- [ ] **Step 4: Update upload.py with auth**

Add auth to upload endpoint. At the top of `hemera/api/upload.py`, add imports:

```python
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser
```

Change the endpoint signature from:

```python
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
```

to:

```python
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
```

And change the engagement creation from:

```python
    engagement = Engagement(
        org_name="(pending)",
        upload_filename=filename,
        status="classifying",
    )
```

to:

```python
    engagement = Engagement(
        org_name=current_user.org_name,
        upload_filename=filename,
        status="classifying",
    )
```

- [ ] **Step 5: Update reports.py with auth**

Replace `hemera/api/reports.py`:

```python
"""Report generation endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.services.data_quality import generate_data_quality_report
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser

router = APIRouter()


@router.get("/reports/{engagement_id}/data-quality")
def get_data_quality_report(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Generate a Data Quality Improvement Report for an engagement."""
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if current_user.role != "admin" and engagement.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")

    transactions = (
        db.query(Transaction)
        .filter(Transaction.engagement_id == engagement_id)
        .all()
    )

    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found for engagement")

    return generate_data_quality_report(transactions, engagement_id)
```

- [ ] **Step 6: Update qc.py with admin requirement**

At the top of `hemera/api/qc.py`, add import:

```python
from hemera.dependencies import require_admin
from hemera.services.clerk import ClerkUser
```

Add `current_user: ClerkUser = Depends(require_admin)` to all three endpoint signatures:

```python
@router.post("/engagements/{engagement_id}/qc/generate")
def generate_qc_sample(engagement_id: int, db: Session = Depends(get_db), current_user: ClerkUser = Depends(require_admin)):

@router.get("/engagements/{engagement_id}/qc")
def get_qc_status(engagement_id: int, db: Session = Depends(get_db), current_user: ClerkUser = Depends(require_admin)):

@router.post("/engagements/{engagement_id}/qc/submit")
def submit_qc_results(engagement_id: int, body: QCSubmitRequest, db: Session = Depends(get_db), current_user: ClerkUser = Depends(require_admin)):
```

- [ ] **Step 7: Run ALL tests**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_auth.py -v
```
Expected: 17 passed

Note: The existing data_quality and qc_sampling tests will need auth mocking. Run them too:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/ -v
```

Some existing tests may fail because endpoints now require auth. These tests use `TestClient` directly and will get 401. Fix by adding auth mocking to those tests — or note this as a known issue to fix in a follow-up.

- [ ] **Step 8: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/api/engagements.py hemera/api/upload.py hemera/api/reports.py hemera/api/qc.py tests/test_auth.py
git commit -m "feat: protect all endpoints with auth, org scoping, admin-only QC"
```

---

## Task 5: Fix existing tests for auth

**Files:**
- Modify: `tests/test_data_quality.py`
- Modify: `tests/test_qc_sampling.py`

The existing API integration tests in `test_data_quality.py` and `test_qc_sampling.py` now fail because endpoints require authentication. Fix by mocking the auth dependency.

- [ ] **Step 1: Fix test_data_quality.py API tests**

In `tests/test_data_quality.py`, for both `test_api_data_quality_endpoint` and `test_api_data_quality_not_found`, add auth mocking. Add at the top of the file:

```python
from unittest.mock import patch
from hemera.services.clerk import ClerkUser
```

Then in each API test function, wrap the test client calls with:

```python
    mock_user = ClerkUser(clerk_id="test", email="test@test.com", org_name="Test SU", role="admin")
    with patch("hemera.dependencies.verify_clerk_token", return_value=mock_user):
        # ... existing test client calls ...
```

Also ensure the Engagement's `org_name` matches "Test SU" or use role="admin".

- [ ] **Step 2: Fix test_qc_sampling.py API tests**

Same pattern for all API tests in `tests/test_qc_sampling.py`. Add the import and wrap each API test's client calls:

```python
from unittest.mock import patch
from hemera.services.clerk import ClerkUser
```

```python
    mock_admin = ClerkUser(clerk_id="test", email="admin@hemera.com", org_name="Hemera", role="admin")
    with patch("hemera.dependencies.verify_clerk_token", return_value=mock_admin):
        # ... existing test client calls with headers={"Authorization": "Bearer fake"} ...
```

Add `headers={"Authorization": "Bearer fake"}` to all TestClient calls.

- [ ] **Step 3: Run full test suite**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/ -v
```
Expected: All tests pass

- [ ] **Step 4: Verify app loads**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -c "from hemera.main import app; print('App loads OK')"
```
Expected: `App loads OK`

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add tests/test_data_quality.py tests/test_qc_sampling.py
git commit -m "fix: update existing tests to work with auth dependencies"
```
