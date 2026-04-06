"""Hemera — FastAPI application."""

from fastapi import FastAPI
from hemera.api import upload, engagements, suppliers, reports, qc

app = FastAPI(
    title="Hemera",
    description="Supply Chain & Carbon Intelligence API",
    version="0.1.0",
)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(engagements.router, prefix="/api", tags=["engagements"])
app.include_router(suppliers.router, prefix="/api", tags=["suppliers"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(qc.router, prefix="/api", tags=["qc"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "hemera"}
