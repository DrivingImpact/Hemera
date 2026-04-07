# Deployment Design — Render + Neon

**Date:** 2026-04-07
**Status:** Approved

## Overview

Deploy the Hemera FastAPI API to Render (free tier) with Neon PostgreSQL (free tier). Zero cost. Auto-deploys from GitHub `main` branch.

## Architecture

```
GitHub (main branch)
  → Render (auto-deploy on push)
    → Docker container: FastAPI + Uvicorn
    → Connects to Neon PostgreSQL via DATABASE_URL
```

**API URL:** `https://hemera-api.onrender.com` (Render assigns this)
**DB:** Neon free tier PostgreSQL 16 (0.5GB storage, 190 compute hours/month)

## Tradeoffs

- Render free tier spins down after 15 minutes of inactivity. First request after idle takes ~30 seconds. Acceptable for early stage.
- Neon free tier has connection limits (100 concurrent). Fine for a consultancy with a handful of active clients.
- No custom domain for now — uses Render's default URL.

## Files to Create/Modify

### Dockerfile

```dockerfile
FROM python:3.14-slim

WORKDIR /app

# System deps for WeasyPrint (PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "hemera.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

WeasyPrint needs system libraries (Pango, Cairo, GDK-Pixbuf) for PDF rendering. These are included in the Docker image.

### requirements.txt

Generated from the current venv. Pins all direct dependencies.

### render.yaml (Render Blueprint)

```yaml
services:
  - type: web
    name: hemera-api
    runtime: docker
    plan: free
    autoDeploy: true
    envVars:
      - key: DATABASE_URL
        sync: false  # set manually from Neon
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

### Startup: Migrations + Seeding

The Dockerfile CMD runs uvicorn directly. Alembic migrations and DEFRA seeding happen via a FastAPI startup event:

```python
@app.on_event("startup")
async def startup():
    # Run Alembic migrations
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    
    # Seed DEFRA factors
    from hemera.database import SessionLocal
    from hemera.services.seed_factors import seed_emission_factors
    db = SessionLocal()
    try:
        seed_emission_factors(db)
    finally:
        db.close()
```

### CORS

Add CORS middleware to `hemera/main.py` for future dashboard access:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to dashboard URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Config Update

Update `hemera/config.py` to handle Neon's connection string format. Neon uses `postgresql://` URLs with SSL required. Add:

```python
@property
def async_database_url(self) -> str:
    """Convert sync URL to async if needed."""
    return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
```

Also ensure `sslmode=require` is handled — Neon requires SSL. The `database_url` from Neon already includes `?sslmode=require`.

## Manual Steps (one-time)

### 1. Create Neon Database

1. Go to https://neon.tech — sign up (free, no credit card)
2. Create a project named "hemera"
3. Copy the connection string: `postgresql://user:pass@ep-xxx.region.aws.neon.tech/hemera?sslmode=require`

### 2. Create Render Service

1. Go to https://render.com — sign up (free, GitHub auth)
2. New → Web Service → Connect GitHub repo `DrivingImpact/Hemera`
3. Render detects the Dockerfile automatically
4. Set environment variables:
   - `DATABASE_URL` = Neon connection string from step 1
   - `CLERK_SECRET_KEY` = your Clerk secret key
   - `CLERK_PUBLISHABLE_KEY` = your Clerk publishable key  
   - `CLERK_WEBHOOK_SECRET` = your Clerk webhook secret
   - `ANTHROPIC_API_KEY` = your Anthropic API key
   - `COMPANIES_HOUSE_API_KEY` = your Companies House API key
5. Deploy

### 3. Verify

```bash
curl https://hemera-api.onrender.com/health
# {"status": "ok", "service": "hemera"}
```

## What This Does NOT Cover

- Custom domain setup (future — when you have a domain)
- Dashboard deployment (Vercel — separate spec when Next.js app exists)
- CI/CD pipeline (Render's auto-deploy from GitHub is sufficient for now)
- Monitoring/alerting (future — add when you have paying clients)
- Backups (Neon handles this on free tier — 7 day retention)
