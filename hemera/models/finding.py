"""HemeraScope findings, report selections, and report actions."""

from datetime import datetime
from sqlalchemy import (
    String, Text, Float, Integer, Boolean, DateTime, JSON,
    Index, UniqueConstraint, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hemera.database import Base


class SupplierFinding(Base):
    """An AI-generated or analyst finding about a supplier."""

    __tablename__ = "supplier_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    ai_task_id: Mapped[int | None] = mapped_column(ForeignKey("ai_tasks.id"))

    domain: Mapped[str] = mapped_column(String(50))  # e.g. carbon_climate, governance_identity
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))  # critical, high, medium, low, info
    confidence: Mapped[float | None] = mapped_column(Float)
    source_layers: Mapped[list | None] = mapped_column(JSON)  # which layers contributed
    evidence: Mapped[dict | None] = mapped_column(JSON)  # supporting data

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    supplier = relationship("Supplier", back_populates="findings", foreign_keys=[supplier_id])
    ai_task = relationship("AITask", foreign_keys=[ai_task_id])
    report_selections = relationship("ReportSelection", back_populates="finding")

    __table_args__ = (
        Index("ix_supplier_findings_active", "supplier_id", "is_active"),
        Index("ix_supplier_findings_domain", "supplier_id", "domain"),
        Index("ix_supplier_findings_severity", "supplier_id", "severity"),
    )


class ReportSelection(Base):
    """Tracks which findings are included/excluded from a client report."""

    __tablename__ = "report_selections"

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.id"), nullable=False)
    finding_id: Mapped[int] = mapped_column(ForeignKey("supplier_findings.id"), nullable=False)

    included: Mapped[bool] = mapped_column(Boolean, default=True)
    selected_by: Mapped[str | None] = mapped_column(String(255))  # email of person who selected
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    engagement = relationship("Engagement", back_populates="report_selections", foreign_keys=[engagement_id])
    finding = relationship("SupplierFinding", back_populates="report_selections", foreign_keys=[finding_id])

    __table_args__ = (
        UniqueConstraint("engagement_id", "finding_id", name="uq_report_selection_engagement_finding"),
    )


class ReportAction(Base):
    """AI-generated content for the supplier report (narratives, charts, etc.)."""

    __tablename__ = "report_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.id"), nullable=False)
    ai_task_id: Mapped[int | None] = mapped_column(ForeignKey("ai_tasks.id"))

    action_type: Mapped[str] = mapped_column(String(50))  # narrative, chart, recommendation
    section: Mapped[str | None] = mapped_column(String(100))  # e.g. executive_summary, methodology
    content: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, approved, rejected
    approved_by: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    engagement = relationship("Engagement", back_populates="report_actions", foreign_keys=[engagement_id])
    ai_task = relationship("AITask", foreign_keys=[ai_task_id])
