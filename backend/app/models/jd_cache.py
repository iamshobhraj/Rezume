"""JD Cache ORM model – caches parsed job descriptions to save LLM calls."""

import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.database import Base


class JDCache(Base):
    """Caches the output of Stage 1 (JD Parsing) by hashing the raw JD text."""

    __tablename__ = "jd_cache"

    jd_hash = Column(String, primary_key=True)  # SHA-256 hex digest
    parsed_json = Column(Text, nullable=False)   # The structured ParseJD output
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
