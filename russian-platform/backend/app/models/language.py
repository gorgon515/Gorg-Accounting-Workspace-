from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Language(Base):
    """A supported target language. Russian is the first; the schema is
    language-agnostic so new languages are added as rows + seed content."""

    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)  # "ru"
    name_english: Mapped[str] = mapped_column(String(64))  # "Russian"
    name_native: Mapped[str] = mapped_column(String(64))  # "Русский"
    script: Mapped[str] = mapped_column(String(32))  # "Cyrillic"
    # Alphabet, phoneme inventory, romanization rules etc.
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
