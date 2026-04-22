"""Client engagements — a single carbon footprint report."""

from datetime import datetime, date
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hemera.database import Base


class Engagement(Base):
    """A client engagement — one carbon footprint analysis."""

    __tablename__ = "engagements"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Client info
    org_name: Mapped[str] = mapped_column(String(255))
    org_type: Mapped[str | None] = mapped_column(String(50))  # su, charity, sme, council, etc.
    contact_email: Mapped[str | None] = mapped_column(String(255))

    # Report metadata
    fiscal_year_start: Mapped[date | None] = mapped_column(Date)
    fiscal_year_end: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    # statuses: uploaded -> classifying -> calculating -> reviewing -> delivered

    # Admin metadata
    uploaded_by_email: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))  # admin-editable label, e.g. "John (SU)"
    admin_notes: Mapped[str | None] = mapped_column(Text)

    # File reference
    upload_filename: Mapped[str | None] = mapped_column(String(255))

    # Results summary (populated after calculation)
    total_co2e: Mapped[float | None] = mapped_column(Float)  # total tCO2e
    scope1_co2e: Mapped[float | None] = mapped_column(Float)
    scope2_co2e: Mapped[float | None] = mapped_column(Float)
    scope3_co2e: Mapped[float | None] = mapped_column(Float)
    gsd_total: Mapped[float | None] = mapped_column(Float)  # overall uncertainty
    ci_lower: Mapped[float | None] = mapped_column(Float)  # 95% CI lower bound
    ci_upper: Mapped[float | None] = mapped_column(Float)  # 95% CI upper bound
    transaction_count: Mapped[int | None] = mapped_column(Integer)
    supplier_count: Mapped[int | None] = mapped_column(Integer)

    # HemeraScope supplier report fields
    supplier_report_status: Mapped[str | None] = mapped_column(String(20))
    supplier_report_exec_summary: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_by: Mapped[str | None] = mapped_column(String(255))

    # Relationships
    transactions = relationship("Transaction", back_populates="engagement")
    report_selections = relationship("ReportSelection", back_populates="engagement")
    report_actions = relationship("ReportAction", back_populates="engagement")
