"""Pydantic schemas for LLM Provider CRUD operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    """Schema for creating a new provider."""

    name: str = Field(..., min_length=1, max_length=100, description="User-friendly label")
    provider_type: str = Field(..., pattern=r"^(google|openai|anthropic|custom)$")
    base_url: Optional[str] = Field(None, description="Base URL for OpenAI-compatible APIs")
    api_key: str = Field(..., min_length=1)
    chat_model: str = Field(..., min_length=1)
    embedding_model: str = Field(..., min_length=1)
    embedding_dim: int = Field(768, ge=1, le=10000)


class ProviderUpdate(BaseModel):
    """Schema for updating an existing provider."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider_type: Optional[str] = Field(None, pattern=r"^(google|openai|anthropic|custom)$")
    base_url: Optional[str] = None
    api_key: Optional[str] = Field(None, min_length=1)
    chat_model: Optional[str] = Field(None, min_length=1)
    embedding_model: Optional[str] = Field(None, min_length=1)
    embedding_dim: Optional[int] = Field(None, ge=1, le=10000)


class ProviderResponse(BaseModel):
    """Schema for provider API responses (API key masked)."""

    id: str
    name: str
    provider_type: str
    base_url: Optional[str] = None
    api_key_masked: str  # Only last 4 chars shown
    chat_model: str
    embedding_model: str
    embedding_dim: int
    is_active_chat: bool
    is_active_embedding: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderActivate(BaseModel):
    """Schema for activating a provider as chat and/or embedding."""

    set_active_chat: bool = False
    set_active_embedding: bool = False


class ProviderTestResponse(BaseModel):
    """Schema for provider connection test result."""

    ok: bool
    message: str
