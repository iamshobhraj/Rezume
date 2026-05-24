"""LLMProvider ORM model – stores user-configured AI provider credentials."""

import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class LLMProvider(Base):
    """Represents a configured LLM/embedding API provider."""

    __tablename__ = "llm_providers"

    id = Column(String, primary_key=True)  # UUID string
    name = Column(String, unique=True, nullable=False)  # user-friendly label
    provider_type = Column(String, nullable=False)  # google | openai | anthropic | custom
    base_url = Column(String, nullable=True)  # for OpenAI-compatible APIs
    api_key = Column(String, nullable=False)
    chat_model = Column(String, nullable=False)  # e.g. "gemini-2.0-flash", "gpt-4o"
    embedding_model = Column(String, nullable=False)  # e.g. "text-embedding-004"
    embedding_dim = Column(Integer, default=768)  # vector dimension for Qdrant
    is_active_chat = Column(Boolean, default=False)
    is_active_embedding = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
