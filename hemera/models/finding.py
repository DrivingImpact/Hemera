"""HemeraScope findings, report selections, and report actions."""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, JSON,
    Index, UniqueConstraint, ForeignKey,
)
from sqlalchemy.orm import relationship
from hemera.database import Base


class SupplierFinding(Base):
    __tablename__ = "supplier_findings"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    source = Column(String(20), nullable=False)  # deterministic, outlier, ai_automated, ai_manual
    domain = Column(String(30), nullable=False)  # governance, labour, carbon, water, product, transparency, anti_corruption, social_value
    severity = Column(String(10), nullable=False)  # critical, high, medium, info, positive
    title = Column(String(255), nullable=False)
    detail = Column(Text, nullable=False)
    evidence_url = Column(Text)
    evidence_data = Column(JSON)
    layer = Column(Integer)  # 1-13, for deterministic findings
    source_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    ai_task_id = Column(Integer, ForeignKey("ai_tasks.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    superseded_at = Column(DateTime)

    supplier = relationship("Supplier", back_populates="findings")
    selections = relationship("ReportSelection", back_populates="finding")

    __table_args__ = (
        Index("ix_supplier_findings_active", "supplier_id", "is_active"),
        Index("ix_supplier_findings_domain", "supplier_id", "domain"),
        Index("ix_supplier_findings_severity", "supplier_id", "severity"),
    )


class ReportSelection(Base):
    __tablename__ = "report_selections"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagements.id"), nullable=False)
    finding_id = Column(Integer, ForeignKey("supplier_findings.id"), nullable=False)
    included = Column(Boolean, nullable=False)
    client_title = Column(String(255))
    client_detail = Column(Text)
    client_language_source = Column(String(20))  # ai_automated, ai_manual, analyst
    analyst_note = Column(Text)
    selected_by = Column(Integer, nullable=False)
    selected_at = Column(DateTime, default=datetime.utcnow)

    finding = relationship("SupplierFinding", back_populates="selections")
    engagement = relationship("Engagement", back_populates="report_selections")

    __table_args__ = (
        UniqueConstraint("engagement_id", "finding_id", name="uq_report_selection_engagement_finding"),
    )


class ReportAction(Base):
    __tablename__ = "report_actions"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagements.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    action_text = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False, default=1)
    linked_finding_ids = Column(JSON)
    language_source = Column(String(20), nullable=False)  # ai_automated, ai_manual, analyst
    ai_task_id = Column(Integer, ForeignKey("ai_tasks.id"))
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    engagement = relationship("Engagement", back_populates="report_actions")
    supplier = relationship("Supplier")
