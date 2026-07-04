from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InstalledPack(Base):
    """Provenance record for an installed content pack: which rows it
    created, so it can be rolled back or upgraded transactionally."""

    __tablename__ = "installed_packs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(24))
    language: Mapped[str] = mapped_column(String(8))
    checksum: Mapped[str] = mapped_column(String(64))
    signed: Mapped[bool] = mapped_column(default=False)
    # {"lexemes": [ids], "texts": [ids], "grammar_topics": [ids], "scenarios": [ids]}
    row_ids: Mapped[dict] = mapped_column(JSON, default=dict)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
