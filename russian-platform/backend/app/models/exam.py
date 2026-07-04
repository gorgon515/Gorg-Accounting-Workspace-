from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExamResult(Base):
    """A completed exam attempt. Passing level exams also serves as the
    certificate record (see /exams/certificates)."""

    __tablename__ = "exam_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # level | placement
    level: Mapped[str] = mapped_column(String(4))  # exam level or placed level
    seed: Mapped[str] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(Float)  # 0..1 overall
    passed: Mapped[bool] = mapped_column(default=False)
    sections: Mapped[dict] = mapped_column(JSON, default=dict)  # per-section scores
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    taken_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
