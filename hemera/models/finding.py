"""HemeraScope findings, report selections, and report actions."""

from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, JSON,
    Index, UniqueConstraint, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hemera.database import Base


class SupplierFinding(Base):
    """A finding about a supplier from any layer or AI analysis."""

    __tablename__ = "supplier_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    source: Mapped[str] = mapped_column(String(20))  # deterministic, outlier, ai_automated, ai_manual
    domain: Mapped[str] = mapped_column(String(30))  # governance, labour, carbon, water, product, transparency, anti_corruption, social_value
    severity: Mapped[str] = mapped_column(String(10))  # critical, high, medium, info, positive
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str | None] = mapped_column(Text)
    evidence_data: Mapped[dict | None] = mapped_column(JSON)
    layer: Mapped[int | None] = mapped_column(Integer)  # 1-13, for deterministic findings
    source_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_task_id: Mapped[int | None] = mapped_column(ForeignKey("ai_tasks.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime)

    supplier = relationship("Supplier", back_populates="findings")
    selections = relationship("ReportSelection", back_populates="finding")

    __table_args__ = (
        Index("ix_supplier_findings_active", "supplier_id", "is_active"),
        Index("ix_supplier_findings_domain", "supplier_id", "domain"),
        Index("ix_supplier_findings_severity", "supplier_id", "severity"),
    )


class ReportSelection(Base):
    """Links a finding to an engagement report — tracks inclusion/exclusion."""

    __tablename__ = "report_selections"

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.id"))
    finding_id: Mapped[int] = mapped_column(ForeignKey("supplier_findings.id"))
    included: Mapped[bool] = mapped_column(Boolean)
    client_title: Mapped[str | None] = mapped_column(String(255))
    client_detail: Mapped[str | None] = mapped_column(Text)
    client_language_source: Mapped[str | None] = mapped_column(String(20))  # ai_automated, ai_manual, analyst
    analyst_note: Mapped[str | None] = mapped_column(Text)
    selected_by: Mapped[int] = mapped_column(Integer)
    selected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    finding = relationship("SupplierFinding", back_populates="selections")
    engagement = relationship("Engagement", back_populates="report_selections")

    __table_args__ = (
        UniqueConstraint("engagement_id", "finding_id", name="uq_report_selection_engagement_finding"),
    )


class ReportAction(Base):
    """A recommended action linked to an engagement and supplier."""

    __tablename__ = "report_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.id"))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    action_text: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    linked_finding_ids: Mapped[list | None] = mapped_column(JSON)
    language_source: Mapped[str] = mapped_column(String(20))  # ai_automated, ai_manual, analyst
    ai_task_id: Mapped[int | None] = mapped_column(ForeignKey("ai_tasks.id"))
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    engagement = relationship("Engagement", back_populates="report_actions")
    supplier = relationship("Supplier")
