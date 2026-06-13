"""WorkEntry and Chunk ORM models – stores typed engineering work and its chunks.

Replaces the old `project.py` model. Key changes:
- EntryType enum (WORK_EXPERIENCE, PROJECT, OSS) for semantic distinction
- Structured start_date/end_date instead of freeform date_range
- Computed date_range property for backward compatibility
"""

import datetime
import enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class EntryType(str, enum.Enum):
    """Semantic type of a work entry."""

    WORK_EXPERIENCE = "work_experience"  # Professional internship, job
    PROJECT = "project"                  # Personal / academic project
    OSS = "oss"                          # Open source contribution


class WorkEntry(Base):
    """A piece of engineering work – typed as work experience, project, or OSS contribution."""

    __tablename__ = "work_entries"

    id = Column(String, primary_key=True)  # UUID string
    entry_type = Column(SQLEnum(EntryType), default=EntryType.PROJECT, nullable=False)
    title = Column(String, nullable=False)
    company = Column(String, nullable=True)  # e.g. "Stripe", "Personal", org name
    role = Column(String, nullable=True)
    start_date = Column(String, nullable=True)   # ISO month: "2024-10"
    end_date = Column(String, nullable=True)     # ISO month or "present"
    raw_text = Column(Text, nullable=False)
    priority = Column(Integer, default=3)  # 1 to 5 stars
    github_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    chunks = relationship("Chunk", back_populates="work_entry", cascade="all, delete-orphan")

    @property
    def date_range(self) -> str:
        """Compute a display date range from structured start/end dates."""
        if not self.start_date:
            return ""
        end = "Present" if self.end_date in (None, "", "present") else self.end_date
        return f"{self.start_date} – {end}"

    # Backward-compat helper: map old project_type to EntryType
    @staticmethod
    def entry_type_from_project_type(project_type: str) -> "EntryType":
        """Map legacy project_type strings to the new EntryType enum."""
        mapping = {
            "personal": EntryType.PROJECT,
            "work": EntryType.WORK_EXPERIENCE,
            "oss": EntryType.OSS,
            "work_experience": EntryType.WORK_EXPERIENCE,
            "project": EntryType.PROJECT,
        }
        return mapping.get(project_type, EntryType.PROJECT)


class Chunk(Base):
    """A text chunk derived from a WorkEntry, with extracted metadata and Qdrant reference."""

    __tablename__ = "chunks"

    id = Column(String, primary_key=True)  # UUID string
    work_entry_id = Column(String, ForeignKey("work_entries.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON: skills, technologies, impact
    qdrant_point_id = Column(String, nullable=True)  # Qdrant point UUID
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    work_entry = relationship("WorkEntry", back_populates="chunks")
