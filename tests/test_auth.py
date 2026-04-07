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

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
_public_key = _private_key.public_key()
_private_pem = _private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
_public_pem = _public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)


def _make_token(claims: dict, expired: bool = False) -> str:
    now = int(time.time())
    payload = {
        "sub": "user_test123", "email": "test@example.com",
        "iat": now, "exp": now - 100 if expired else now + 3600,
        "public_metadata": {"org_name": "Test SU", "role": "client"},
        **claims,
    }
    return jwt.encode(payload, _private_pem, algorithm="RS256", headers={"kid": "test-key-id"})


def _mock_jwks_client():
    """Create a mock PyJWKClient that returns our test key."""
    mock_client = MagicMock()
    mock_signing_key = MagicMock()
    mock_signing_key.key = _public_pem
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
    return mock_client


@patch("hemera.services.clerk._get_jwks_client")
def test_verify_valid_token(mock_get_client):
    mock_get_client.return_value = _mock_jwks_client()
    token = _make_token({})
    user = verify_clerk_token(token)
    assert user.clerk_id == "user_test123"
    assert user.email == "test@example.com"
    assert user.org_name == "Test SU"
    assert user.role == "client"


@patch("hemera.services.clerk._get_jwks_client")
def test_verify_admin_token(mock_get_client):
    mock_get_client.return_value = _mock_jwks_client()
    token = _make_token({"public_metadata": {"org_name": "Hemera", "role": "admin"}})
    user = verify_clerk_token(token)
    assert user.role == "admin"
    assert user.org_name == "Hemera"


@patch("hemera.services.clerk._get_jwks_client")
def test_verify_expired_token(mock_get_client):
    mock_get_client.return_value = _mock_jwks_client()
    token = _make_token({}, expired=True)
    user = verify_clerk_token(token)
    assert user is None


def test_verify_invalid_token():
    user = verify_clerk_token("not.a.real.token")
    assert user is None


@patch("hemera.services.clerk._get_jwks_client")
def test_verify_missing_metadata(mock_get_client):
    mock_get_client.return_value = _mock_jwks_client()
    token = _make_token({"public_metadata": {}})
    user = verify_clerk_token(token)
    assert user is not None
    assert user.role == "client"
    assert user.org_name == ""


from fastapi import HTTPException
from hemera.dependencies import get_current_user, require_admin


def test_get_current_user_valid():
    mock_user = ClerkUser(clerk_id="user_1", email="a@b.com", org_name="TestOrg", role="client")
    with patch("hemera.dependencies.verify_clerk_token", return_value=mock_user):
        user = get_current_user(token="fake_token")
        assert user.clerk_id == "user_1"
        assert user.org_name == "TestOrg"


def test_get_current_user_no_token():
    with pytest.raises(HTTPException) as exc:
        get_current_user(token="")
    assert exc.value.status_code == 401


def test_get_current_user_invalid_token():
    with patch("hemera.dependencies.verify_clerk_token", return_value=None):
        with pytest.raises(HTTPException) as exc:
            get_current_user(token="bad_token")
        assert exc.value.status_code == 401


def test_require_admin_with_admin():
    admin = ClerkUser(clerk_id="user_1", email="a@b.com", org_name="Hemera", role="admin")
    result = require_admin(current_user=admin)
    assert result.role == "admin"


def test_require_admin_with_client():
    client_user = ClerkUser(clerk_id="user_2", email="b@c.com", org_name="TestOrg", role="client")
    with pytest.raises(HTTPException) as exc:
        require_admin(current_user=client_user)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Task 3: API auth endpoints and webhook
# ---------------------------------------------------------------------------

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
    client = TestClient(app)
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_webhook_creates_user():
    session = _make_test_session()
    def override_get_db():
        try: yield session
        finally: pass
    app.dependency_overrides[get_db] = override_get_db
    payload = {
        "type": "user.created",
        "data": {
            "id": "user_clerk_abc",
            "email_addresses": [{"email_address": "new@su.ac.uk"}],
            "public_metadata": {"org_name": "Test SU", "role": "client"},
        },
    }
    with patch("hemera.api.auth._verify_webhook_signature", return_value=True):
        client = TestClient(app)
        r = client.post("/api/webhooks/clerk", json=payload)
        assert r.status_code == 200
    user = session.query(User).filter(User.clerk_id == "user_clerk_abc").first()
    assert user is not None
    assert user.email == "new@su.ac.uk"
    assert user.org_name == "Test SU"
    assert user.role == "client"
    app.dependency_overrides.clear()
    session.close()


# ---------------------------------------------------------------------------
# Task 4: Org scoping and endpoint protection tests
# ---------------------------------------------------------------------------

from hemera.models.engagement import Engagement


def test_engagements_scoped_to_org():
    session = _make_test_session()
    def override_get_db():
        try: yield session
        finally: pass
    app.dependency_overrides[get_db] = override_get_db
    e1 = Engagement(org_name="Imperial SU", status="delivered", transaction_count=5)
    e2 = Engagement(org_name="Other SU", status="delivered", transaction_count=3)
    session.add_all([e1, e2])
    session.flush()
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


def test_upload_requires_auth():
    client = TestClient(app)
    r = client.post("/api/upload")
    assert r.status_code in (401, 422)
