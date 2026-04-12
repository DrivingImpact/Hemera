"""Hemera — FastAPI application."""

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from hemera.api import upload, engagements, suppliers, reports, qc, auth, supplier_review, findings, ai_tasks, hemerascope, export

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
    allow_origins=[
        "http://localhost:3000",
        "https://hemera-nx8p.vercel.app",
        "https://hemera-nx8p-drivingimpacts-projects.vercel.app",
    ],
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
app.include_router(supplier_review.router, prefix="/api", tags=["supplier-review"])
app.include_router(findings.router, prefix="/api", tags=["findings"])
app.include_router(ai_tasks.router, prefix="/api", tags=["ai-tasks"])
app.include_router(hemerascope.router, prefix="/api", tags=["hemerascope"])
app.include_router(export.router, prefix="/api", tags=["export"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log unhandled errors and return details (visible in Render logs)."""
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok", "service": "hemera"}
