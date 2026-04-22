"""Emission factor lookup table — local copy of DEFRA, Exiobase, etc."""

from sqlalchemy import String, Float, Integer, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column
from hemera.database import Base


class EmissionFactor(Base):
    """A single emission factor from DEFRA, Exiobase, USEEIO, etc.
    Pre-loaded from downloaded datasets."""

    __tablename__ = "emission_factors"

    id: Mapped[int] = mapped_column(primary_key=True)

    source: Mapped[str] = mapped_column(String(50), index=True)  # defra, exiobase, useeio
    category: Mapped[str] = mapped_column(String(255))  # e.g. "Electricity: UK grid"
    subcategory: Mapped[str | None] = mapped_column(String(255))
    scope: Mapped[int | None] = mapped_column(Integer)  # which scope this factor applies to

    factor_value: Mapped[float] = mapped_column(Float)  # the actual factor
    unit: Mapped[str] = mapped_column(String(50))  # kgCO2e/kWh, kgCO2e/GBP, kgCO2e/km, etc.
    factor_type: Mapped[str] = mapped_column(String(20))  # activity, spend
    year: Mapped[int] = mapped_column(Integer)  # factor year
    region: Mapped[str] = mapped_column(String(50), default="UK")

    # For keyword matching
    keywords: Mapped[str | None] = mapped_column(String(500))  # comma-separated match terms

    # Source traceability — which sheet/row in the original DEFRA Excel
    source_sheet: Mapped[str | None] = mapped_column(String(100))
    source_row: Mapped[int | None] = mapped_column(Integer)
    source_hierarchy: Mapped[list | None] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_ef_source_category", "source", "category"),
        Index("ix_ef_scope_type", "scope", "factor_type"),
    )
