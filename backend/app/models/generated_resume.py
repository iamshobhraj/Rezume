"""GeneratedResume ORM model – stores generated resume artifacts."""

import datetime

from sqlalchemy import Column, DateTime, Float, String, Text

from app.database import Base


class GeneratedResume(Base):
    """A resume generated for a specific job description."""

    __tablename__ = "generated_resumes"

    id = Column(String, primary_key=True)  # UUID string
    job_description = Column(Text, nullable=False)
    generated_content = Column(Text, nullable=True)  # Structured resume JSON
    generated_latex = Column(Text, nullable=True)
    pdf_path = Column(String, nullable=True)
    score = Column(Float, nullable=True)  # ATS compatibility score
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
