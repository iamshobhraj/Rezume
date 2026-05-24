"""Pydantic schemas for resume generation operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ResumeGenerateRequest(BaseModel):
    """Schema for requesting resume generation."""

    job_description: str = Field(..., min_length=10)


class ResumeResponse(BaseModel):
    """Schema for generated resume API responses."""

    id: str
    job_description: str
    generated_content: Optional[str] = None
    generated_latex: Optional[str] = None
    pdf_path: Optional[str] = None
    score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeListResponse(BaseModel):
    """Schema for listing generated resumes (without full content)."""

    id: str
    job_description_preview: str  # First 200 chars
    score: Optional[float] = None
    has_pdf: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
