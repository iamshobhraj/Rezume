"""Pydantic schemas for resume configuration."""

from typing import Optional

from pydantic import BaseModel


class ResumeConfigData(BaseModel):
    """The JSON payload stored in the resume_config table."""

    target_role: str = ""
    years_experience: int = 0
    skills_emphasis: list[str] = []
    tone: str = "professional"  # professional | concise | detailed
    active_chat_provider_id: Optional[str] = None
    active_embedding_provider_id: Optional[str] = None


class ResumeConfigUpdate(BaseModel):
    """Schema for updating resume configuration."""

    target_role: Optional[str] = None
    years_experience: Optional[int] = None
    skills_emphasis: Optional[list[str]] = None
    tone: Optional[str] = None
    active_chat_provider_id: Optional[str] = None
    active_embedding_provider_id: Optional[str] = None


class ResumeConfigResponse(BaseModel):
    """Schema for resume config API response."""

    target_role: str = ""
    years_experience: int = 0
    skills_emphasis: list[str] = []
    tone: str = "professional"
    active_chat_provider_id: Optional[str] = None
    active_embedding_provider_id: Optional[str] = None
