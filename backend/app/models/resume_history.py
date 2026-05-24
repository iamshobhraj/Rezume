"""Resume History ORM model – stores past generated resumes for diffing."""

import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.database import Base


class ResumeHistory(Base):
    """A past generated resume state, tracked for diffing and history."""

    __tablename__ = "resume_history"

    id = Column(String, primary_key=True)  # UUID string
    generated_resume_id = Column(String, nullable=False) # Reference to GeneratedResume, though we just store the payload
    tags = Column(String, nullable=True) # Comma-separated tags, e.g. "Draft 1, V2"
    resume_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
