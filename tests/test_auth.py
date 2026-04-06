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
    return jwt.encode(payload, _private_pem, algorithm="RS256")


@patch("hemera.services.clerk._get_clerk_public_key")
def test_verify_valid_token(mock_get_key):
    mock_get_key.return_value = _public_pem
    token = _make_token({})
    user = verify_clerk_token(token)
    assert user.clerk_id == "user_test123"
    assert user.email == "test@example.com"
    assert user.org_name == "Test SU"
    assert user.role == "client"


@patch("hemera.services.clerk._get_clerk_public_key")
def test_verify_admin_token(mock_get_key):
    mock_get_key.return_value = _public_pem
    token = _make_token({"public_metadata": {"org_name": "Hemera", "role": "admin"}})
    user = verify_clerk_token(token)
    assert user.role == "admin"
    assert user.org_name == "Hemera"


@patch("hemera.services.clerk._get_clerk_public_key")
def test_verify_expired_token(mock_get_key):
    mock_get_key.return_value = _public_pem
    token = _make_token({}, expired=True)
    user = verify_clerk_token(token)
    assert user is None


def test_verify_invalid_token():
    user = verify_clerk_token("not.a.real.token")
    assert user is None


@patch("hemera.services.clerk._get_clerk_public_key")
def test_verify_missing_metadata(mock_get_key):
    mock_get_key.return_value = _public_pem
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
