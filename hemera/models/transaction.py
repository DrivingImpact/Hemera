"""Transaction line items — each row from the client's accounting data."""

from datetime import datetime, date
from sqlalchemy import (
    String, Text, Float, Integer, Boolean, DateTime, Date, JSON, Index, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hemera.database import Base


class Transaction(Base):
    """A single line item from the client's accounting CSV.
    Every calculation is fully traceable back to this record."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.id"), index=True)

    # Source data (exactly as uploaded)
    row_number: Mapped[int] = mapped_column(Integer)
    raw_date: Mapped[str | None] = mapped_column(String(50))
    raw_description: Mapped[str | None] = mapped_column(Text)
    raw_supplier: Mapped[str | None] = mapped_column(String(255))
    raw_amount: Mapped[float | None] = mapped_column(Float)
    raw_category: Mapped[str | None] = mapped_column(String(255))  # original nominal code

    # Parsed & normalised
    transaction_date: Mapped[date | None] = mapped_column(Date)
    amount_gbp: Mapped[float | None] = mapped_column(Float)

    # Classification
    scope: Mapped[int | None] = mapped_column(Integer)  # 1, 2, or 3
    ghg_category: Mapped[int | None] = mapped_column(Integer)  # 1-15 for Scope 3
    category_name: Mapped[str | None] = mapped_column(String(100))
    classification_method: Mapped[str | None] = mapped_column(String(20))  # keyword, llm, manual
    classification_confidence: Mapped[float | None] = mapped_column(Float)

    # Supplier link
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), index=True)
    supplier_match_method: Mapped[str | None] = mapped_column(String(20))  # exact, fuzzy, new

    # Emission factor applied
    ef_value: Mapped[float | None] = mapped_column(Float)  # emission factor value
    ef_unit: Mapped[str | None] = mapped_column(String(50))  # kgCO2e/GBP, kgCO2e/kWh, etc.
    ef_source: Mapped[str | None] = mapped_column(String(50))  # defra, exiobase, supplier, climatiq
    ef_level: Mapped[int | None] = mapped_column(Integer)  # 1-6 (cascade level)
    ef_year: Mapped[int | None] = mapped_column(Integer)  # year of the emission factor
    ef_region: Mapped[str | None] = mapped_column(String(50))  # UK, EU, global, etc.

    # Calculated emissions
    co2e_kg: Mapped[float | None] = mapped_column(Float)  # calculated kgCO2e

    # Pedigree matrix scores (1-5 each)
    pedigree_reliability: Mapped[int | None] = mapped_column(Integer)
    pedigree_completeness: Mapped[int | None] = mapped_column(Integer)
    pedigree_temporal: Mapped[int | None] = mapped_column(Integer)
    pedigree_geographical: Mapped[int | None] = mapped_column(Integer)
    pedigree_technological: Mapped[int | None] = mapped_column(Integer)
    gsd_total: Mapped[float | None] = mapped_column(Float)  # calculated GSD for this line

    # QC
    is_sampled: Mapped[bool] = mapped_column(Boolean, default=False)
    qc_pass: Mapped[bool | None] = mapped_column(Boolean)
    qc_notes: Mapped[str | None] = mapped_column(Text)

    # Flags
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    engagement = relationship("Engagement", back_populates="transactions", foreign_keys=[engagement_id])
    supplier = relationship("Supplier", back_populates="transactions", foreign_keys=[supplier_id])

    __table_args__ = (
        Index("ix_transactions_engagement_scope", "engagement_id", "scope"),
    )
