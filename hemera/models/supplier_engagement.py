"""Supplier engagement tracking — outreach, data requests, follow-ups."""

from datetime import datetime, date
from sqlalchemy import String, Text, Integer, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from hemera.database import Base


class SupplierEngagement(Base):
    """Tracks direct engagement/outreach with a supplier."""

    __tablename__ = "supplier_engagements"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)

    engagement_type: Mapped[str] = mapped_column(String(50))  # data_request, follow_up, audit, etc.
    subject: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, sent, responded, closed
    notes: Mapped[str | None] = mapped_column(Text)

    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255))

    contacted_at: Mapped[datetime | None] = mapped_column(DateTime)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime)

    next_action: Mapped[str | None] = mapped_column(String(255))
    next_action_date: Mapped[date | None] = mapped_column(Date)

    created_by: Mapped[int | None] = mapped_column(Integer)  # user id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    supplier = relationship("Supplier", back_populates="hemera_engagements", foreign_keys=[supplier_id])
