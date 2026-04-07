# Deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Hemera API deployable to Render (free tier) with Neon PostgreSQL, with auto-deploy from GitHub.

**Architecture:** Dockerfile builds Python 3.14 image with WeasyPrint system deps. Render auto-deploys from `main` branch. Alembic migrations and DEFRA seeding run on FastAPI startup. CORS enabled for future dashboard.

**Tech Stack:** Docker, Render, Neon PostgreSQL, Alembic, Uvicorn

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `Dockerfile` | Create | Build the container image |
| `requirements.txt` | Create | Pin all Python dependencies |
| `render.yaml` | Create | Render blueprint for one-click deploy |
| `.dockerignore` | Create | Exclude venv, pycache, etc from image |
| `hemera/main.py` | Modify | Add CORS middleware + startup event |
| `hemera/database.py` | Modify | Handle Neon SSL connection strings |

---

### Task 1: requirements.txt and .dockerignore

**Files:**
- Create: `requirements.txt`
- Create: `.dockerignore`

- [ ] **Step 1: Generate requirements.txt from current venv**

```bash
.venv/bin/pip freeze | grep -v "^-e" > requirements.txt
```

Verify it contains the key packages:

```bash
grep -E "fastapi|sqlalchemy|alembic|plotly|weasyprint|uvicorn|pyjwt" requirements.txt
```

Expected: all 7 packages present.

- [ ] **Step 2: Create .dockerignore**

Create `.dockerignore`:

```
.venv/
__pycache__/
*.pyc
.env
.env.example
.git/
.gitignore
*.pdf
tests/
docs/
.superpowers/
.DS_Store
test-report*.pdf
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt .dockerignore
git commit -m "chore: add requirements.txt and .dockerignore for deployment"
```

---

### Task 2: Dockerfile and render.yaml

**Files:**
- Create: `Dockerfile`
- Create: `render.yaml`

- [ ] **Step 1: Create Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM python:3.14-slim

WORKDIR /app

# System deps for WeasyPrint (PDF generation needs Pango, Cairo, GDK-Pixbuf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "hemera.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Note: `fonts-liberation` provides a fallback font for WeasyPrint. Plus Jakarta Sans is loaded via Google Fonts URL in the CSS.

- [ ] **Step 2: Create render.yaml**

Create `render.yaml`:

```yaml
services:
  - type: web
    name: hemera-api
    runtime: docker
    plan: free
    autoDeploy: true
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: CLERK_SECRET_KEY
        sync: false
      - key: CLERK_PUBLISHABLE_KEY
        sync: false
      - key: CLERK_WEBHOOK_SECRET
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: COMPANIES_HOUSE_API_KEY
        sync: false
```

- [ ] **Step 3: Test Docker build locally**

```bash
docker build -t hemera-api .
```

Expected: build completes successfully. If Python 3.14-slim is not available on Docker Hub yet, fall back to `python:3.13-slim` in the Dockerfile.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile render.yaml
git commit -m "feat: add Dockerfile and Render blueprint for deployment"
```

---

### Task 3: CORS middleware + startup event

**Files:**
- Modify: `hemera/main.py`

- [ ] **Step 1: Add CORS and startup event to main.py**

Replace the entire contents of `hemera/main.py` with:

```python
"""Hemera — FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hemera.api import upload, engagements, suppliers, reports, qc, auth

logger = logging.getLogger("hemera")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run migrations and seed data on startup."""
    # Run Alembic migrations
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations complete.")
    except Exception as e:
        logger.warning(f"Migration skipped: {e}")

    # Seed DEFRA emission factors
    try:
        from hemera.database import SessionLocal
        from hemera.services.seed_factors import seed_emission_factors
        db = SessionLocal()
        try:
            n = seed_emission_factors(db)
            if n > 0:
                logger.info(f"Seeded {n} emission factors.")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Seeding skipped: {e}")

    yield


app = FastAPI(
    title="Hemera",
    description="Supply Chain & Carbon Intelligence API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to dashboard URL when deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

Uses the modern `lifespan` context manager (not deprecated `on_event`). Migrations and seeding are wrapped in try/except so the app still starts if the DB isn't ready yet (useful for health checks during deployment).

- [ ] **Step 2: Run tests to verify nothing broke**

```bash
.venv/bin/python -m pytest tests/ --tb=short -q
```

Expected: all 136 tests pass.

- [ ] **Step 3: Commit**

```bash
git add hemera/main.py
git commit -m "feat: add CORS middleware and startup migrations/seeding for deployment"
```

---

### Task 4: Database SSL handling for Neon

**Files:**
- Modify: `hemera/database.py`

- [ ] **Step 1: Update database.py to handle Neon SSL**

Replace the entire contents of `hemera/database.py` with:

```python
"""Database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from hemera.config import get_settings

settings = get_settings()

# Neon requires SSL; the connection string includes ?sslmode=require
# SQLAlchemy handles this via the URL parameters
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # verify connections before use (handles Neon cold starts)
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session, auto-closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Key changes:
- `pool_pre_ping=True` — handles Neon's serverless cold starts by verifying connections
- `pool_size=5, max_overflow=10` — respects Neon's 100 connection limit
- Comment explaining Neon's SSL requirement

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python -m pytest tests/ --tb=short -q
```

Expected: all 136 tests pass (tests use in-memory SQLite, not affected by pool settings).

- [ ] **Step 3: Commit**

```bash
git add hemera/database.py
git commit -m "feat: add connection pooling and SSL handling for Neon PostgreSQL"
```

---

### Task 5: Push to GitHub and verify

- [ ] **Step 1: Run full test suite one final time**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: all 136 tests pass.

- [ ] **Step 2: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 3: Verify Render detects the repo (manual)**

After the user creates their Render account and connects the repo, Render will auto-detect the Dockerfile and deploy. The user then sets environment variables and verifies with:

```bash
curl https://hemera-api.onrender.com/health
```
