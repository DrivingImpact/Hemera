"""Supplier Registry — the core asset."""

from datetime import datetime
from sqlalchemy import (
    String, Text, Float, Integer, Boolean, DateTime, JSON,
    Index, UniqueConstraint, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hemera.database import Base


class Supplier(Base):
    """A supplier entity in the registry. Companies House number is the
    canonical identifier for UK entities."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Companies House number — unique canonical key for UK companies
    ch_number: Mapped[str | None] = mapped_column(String(10), unique=True, index=True)
    # Hemera internal ID — persists even if CH number changes (rare but possible)
    hemera_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)

    name: Mapped[str] = mapped_column(String(255), index=True)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(50))  # active, dissolved, etc.
    sic_codes: Mapped[list | None] = mapped_column(JSON)
    sector: Mapped[str | None] = mapped_column(String(100))
    registered_address: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(50))  # ltd, plc, charity, cic, etc.

    # Current ESG score (latest)
    esg_score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[str | None] = mapped_column(String(10))  # high, medium, low
    critical_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    scores = relationship("SupplierScore", back_populates="supplier", order_by="SupplierScore.scored_at.desc()")
    sources = relationship("SupplierSource", back_populates="supplier")
    transactions = relationship("Transaction", back_populates="supplier")
    alerts = relationship("MonitoringAlert", back_populates="supplier")


class SupplierScore(Base):
    """ESG score history — append-only. Every re-scoring creates a new row."""

    __tablename__ = "supplier_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)

    # 7 domain scores (0-100 each)
    governance_identity: Mapped[float | None] = mapped_column(Float)
    labour_ethics: Mapped[float | None] = mapped_column(Float)
    carbon_climate: Mapped[float | None] = mapped_column(Float)
    water_biodiversity: Mapped[float | None] = mapped_column(Float)
    product_supply_chain: Mapped[float | None] = mapped_column(Float)
    transparency_disclosure: Mapped[float | None] = mapped_column(Float)
    anti_corruption: Mapped[float | None] = mapped_column(Float)
    social_value: Mapped[float | None] = mapped_column(Float)

    # Weighted total
    total_score: Mapped[float | None] = mapped_column(Float)

    # Modifiers applied
    critical_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    staleness_penalty: Mapped[float] = mapped_column(Float, default=1.0)
    confidence: Mapped[str | None] = mapped_column(String(10))
    layers_completed: Mapped[int] = mapped_column(Integer, default=0)

    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="scores", foreign_keys=[supplier_id])

    __table_args__ = (
        Index("ix_supplier_scores_supplier_date", "supplier_id", "scored_at"),
    )


class SupplierSource(Base):
    """Raw data collected from each source for each supplier.
    This is the evidence trail — every data point tracked."""

    __tablename__ = "supplier_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)

    layer: Mapped[int] = mapped_column(Integer)  # 1-13
    source_name: Mapped[str] = mapped_column(String(100))  # e.g. "companies_house"
    tier: Mapped[int] = mapped_column(Integer)  # 1-4 (source reliability)
    data: Mapped[dict | None] = mapped_column(JSON)  # raw response data
    summary: Mapped[str | None] = mapped_column(Text)  # human-readable summary

    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)  # staleness tracking
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    supplier = relationship("Supplier", back_populates="sources", foreign_keys=[supplier_id])

    __table_args__ = (
        Index("ix_supplier_sources_layer", "supplier_id", "layer"),
    )


class MonitoringAlert(Base):
    """Intelligence Feed — rolling alerts for supplier changes."""

    __tablename__ = "monitoring_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)

    alert_type: Mapped[str] = mapped_column(String(50))  # filing_change, sanction_hit, cert_expiry, etc.
    source: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))  # critical, warning, info
    detail: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="alerts", foreign_keys=[supplier_id])
