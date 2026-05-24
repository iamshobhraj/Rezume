"""Project and Chunk ORM models – stores raw engineering work and its chunks."""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Project(Base):
    """A piece of engineering work (project, feature, OSS contribution, etc.)."""

    __tablename__ = "projects"

    id = Column(String, primary_key=True)  # UUID string
    title = Column(String, nullable=False)
    company = Column(String, nullable=True)  # e.g. "Personal Project", "Stripe"
    role = Column(String, nullable=True)
    date_range = Column(String, nullable=True)
    raw_text = Column(Text, nullable=False)
    project_type = Column(String, default="personal")  # "personal" or "oss"
    priority = Column(Integer, default=3)  # 1 to 5 stars
    github_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    chunks = relationship("Chunk", back_populates="project", cascade="all, delete-orphan")


class Chunk(Base):
    """A text chunk derived from a Project, with extracted metadata and Qdrant reference."""

    __tablename__ = "chunks"

    id = Column(String, primary_key=True)  # UUID string
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON: skills, technologies, impact
    qdrant_point_id = Column(String, nullable=True)  # Qdrant point UUID
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    project = relationship("Project", back_populates="chunks")
