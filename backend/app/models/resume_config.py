"""ResumeConfig ORM model – singleton config for resume generation preferences."""

import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.database import Base


class ResumeConfig(Base):
    """Singleton row storing user resume generation preferences as a JSON blob."""

    __tablename__ = "resume_config"

    id = Column(String, primary_key=True, default="default")
    config_json = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
