"""AI task tracking — logs every LLM call for audit and cost tracking."""

from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from hemera.database import Base


class AITask(Base):
    """Record of an AI/LLM task execution."""

    __tablename__ = "ai_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    task_type: Mapped[str] = mapped_column(String(50))  # finding_generation, report_narrative, etc.
    target_type: Mapped[str] = mapped_column(String(50))  # supplier, engagement, etc.
    target_id: Mapped[int] = mapped_column(Integer)

    mode: Mapped[str] = mapped_column(String(20), default="auto")  # auto, manual
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed

    prompt_text: Mapped[str] = mapped_column(Text)
    response_text: Mapped[str | None] = mapped_column(Text)
    prompt_hash: Mapped[str] = mapped_column(String(64))  # for deduplication

    token_count: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
