"""Pydantic schemas for Project and Chunk operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    title: str = Field(..., min_length=1, max_length=200)
    company: Optional[str] = None
    role: Optional[str] = None
    date_range: Optional[str] = None
    raw_text: str = Field(..., min_length=1)
    project_type: str = Field("personal")
    priority: int = Field(3, ge=1, le=5)
    github_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    company: Optional[str] = None
    role: Optional[str] = None
    date_range: Optional[str] = None
    raw_text: Optional[str] = Field(None, min_length=1)
    project_type: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    github_url: Optional[str] = None


class ChunkResponse(BaseModel):
    """Schema for chunk data in API responses."""

    id: str
    chunk_text: str
    metadata_json: Optional[str] = None
    qdrant_point_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    """Schema for project API responses."""

    id: str
    title: str
    company: Optional[str] = None
    role: Optional[str] = None
    date_range: Optional[str] = None
    raw_text: str
    project_type: str
    priority: int
    github_url: Optional[str] = None
    created_at: datetime
    chunk_count: int = 0

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    """Schema for project with its chunks."""

    chunks: list[ChunkResponse] = []


class RepoDigestRequest(BaseModel):
    """Schema for digesting a GitHub repository."""

    github_url: str

