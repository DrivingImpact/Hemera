# Auth — Clerk Integration Design Spec

**Date:** 2026-04-06
**Status:** Approved
**Scope:** Clerk JWT verification, org-scoped endpoints, admin role checks, user sync webhook

---

## 1. Purpose

Secure all API endpoints with authentication using Clerk as the identity provider.
Clerk handles registration, login, password management, and token issuance. Hemera's
API verifies Clerk JWTs and enforces org-scoped data access with two roles: client
and admin.

---

## 2. How It Works

1. User signs up/logs in via Clerk (hosted page or React components in future dashboard)
2. Clerk issues a JWT signed with RS256
3. Client sends token: `Authorization: Bearer <token>`
4. Hemera verifies JWT against Clerk's JWKS public keys
5. Extracts user_id, email, org_name, role from token claims/metadata
6. Org scoping and role checks applied per endpoint

---

## 3. Roles

Two roles stored in Clerk's `public_metadata`:

| Role | Access |
|------|--------|
| `client` | Own org's engagements, reports, supplier data only |
| `admin` | All engagements, QC endpoints, all orgs |

Set via Clerk dashboard or Clerk API when onboarding users.

---

## 4. CurrentUser Dataclass

Every protected endpoint receives this:

```python
@dataclass
class CurrentUser:
    clerk_id: str       # Clerk's user ID (sub claim)
    email: str          # from JWT claims
    org_name: str       # from public_metadata
    role: str           # "client" or "admin"
```

---

## 5. FastAPI Dependencies

### `get_current_user`

- Reads `Authorization: Bearer <token>` header
- Fetches Clerk's JWKS from `https://<clerk-domain>/.well-known/jwks.json` (cached)
- Verifies JWT signature (RS256) and expiry
- Extracts claims and public_metadata
- Returns `CurrentUser` dataclass
- Raises 401 if token missing, expired, or invalid

### `require_admin`

- Calls `get_current_user`
- Raises 403 if `role != "admin"`

---

## 6. Endpoint Protection

### Public (no auth)
- `GET /health`
- `POST /api/webhooks/clerk` (verified by Clerk webhook signature, not JWT)

### Authenticated (get_current_user)
- `GET /api/auth/me` — returns current user info
- `GET /api/engagements` — filtered by org_name (admins see all)
- `GET /api/engagements/{id}` — verify org ownership (admins bypass)
- `POST /api/upload` — auto-set org_name from current_user
- `GET /api/reports/{id}/data-quality` — verify org ownership
- `GET /api/suppliers` — filtered by org (admins see all)
- `GET /api/suppliers/{id}` — verify org ownership

### Admin only (require_admin)
- `POST /api/engagements/{id}/qc/generate`
- `GET /api/engagements/{id}/qc`
- `POST /api/engagements/{id}/qc/submit`

---

## 7. Org Scoping Logic

For client users, every engagement query adds:
```python
.filter(Engagement.org_name == current_user.org_name)
```

For admin users, no filter applied.

Upload endpoint auto-sets:
```python
engagement.org_name = current_user.org_name
```

---

## 8. User Sync Webhook

`POST /api/webhooks/clerk` — receives Clerk webhook events.

**Events handled:**
- `user.created` → create User record in DB
- `user.updated` → update User record
- `user.deleted` → deactivate User record (soft delete: `is_active = False`)

**Verification:** Clerk signs webhooks with Svix. The endpoint verifies the
signature using the webhook signing secret before processing. Rejects unverified
payloads with 400.

**For local development:** Webhook endpoint exists but signature verification
can be skipped when `CLERK_WEBHOOK_SECRET` is not set in `.env`.

---

## 9. Model Changes

Update existing User model (`hemera/models/user.py`):

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255))  # unused with Clerk, kept for compatibility
    org_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="client")  # "client" or "admin"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)  # kept for backward compat, derived from role

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

New fields: `clerk_id`, `role`. `hashed_password` made nullable (Clerk manages passwords).
One Alembic migration.

---

## 10. Config Changes

Add to `hemera/config.py` Settings:

```python
clerk_secret_key: str = ""
clerk_publishable_key: str = ""
clerk_webhook_secret: str = ""
clerk_jwks_url: str = ""  # auto-derived from publishable key if not set
```

---

## 11. Architecture

### New files

| File | Purpose |
|------|---------|
| `hemera/services/clerk.py` | JWKS fetching (cached), JWT verification, token parsing |
| `hemera/api/auth.py` | `GET /api/auth/me`, `POST /api/webhooks/clerk` |
| `hemera/dependencies.py` | `get_current_user`, `require_admin` dependencies |

### Modified files

| File | Change |
|------|--------|
| `hemera/models/user.py` | Add `clerk_id`, `role` fields, make `hashed_password` nullable |
| `hemera/config.py` | Add Clerk config settings |
| `hemera/main.py` | Register auth router |
| `hemera/api/engagements.py` | Add auth dependency, org-scope queries |
| `hemera/api/upload.py` | Add auth dependency, auto-set org_name |
| `hemera/api/reports.py` | Add auth dependency, verify org ownership |
| `hemera/api/qc.py` | Add require_admin dependency |

### New dependencies

- `pyjwt[crypto]` — JWT verification with RS256
- `svix` — Clerk webhook signature verification

### Migration

One Alembic migration: add `clerk_id` and `role` to users table, make
`hashed_password` nullable.

---

## 12. Testing Strategy

- Unit tests for JWT verification (mock JWKS, valid/expired/invalid tokens)
- Unit tests for org scoping logic
- API integration tests: authenticated requests, 401 on missing token, 403 on
  non-admin accessing QC
- Webhook tests: valid payload creates user, invalid signature rejected

---

## 13. What This Does NOT Include

- Clerk React components (dashboard feature, separate priority)
- MFA enforcement (can enable in Clerk dashboard at any time, no code change)
- Password reset flow (Clerk handles this entirely)
- User management UI (use Clerk dashboard for now)
- Rate limiting (Clerk handles on their side; API-side rate limiting is a future item)
