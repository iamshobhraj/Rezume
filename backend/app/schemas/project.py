"""Pydantic schemas for WorkEntry (formerly Project), Chunk, and UserSkill operations."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# EntryType enum mirrored from the ORM model for API validation
# ---------------------------------------------------------------------------

class EntryTypeEnum(str, Enum):
    """Matches models.work_entry.EntryType."""

    WORK_EXPERIENCE = "work_experience"
    PROJECT = "project"
    OSS = "oss"


# ---------------------------------------------------------------------------
# WorkEntry schemas
# ---------------------------------------------------------------------------

class WorkEntryCreate(BaseModel):
    """Schema for creating a new work entry."""

    title: str = Field(..., min_length=1, max_length=200)
    entry_type: EntryTypeEnum = Field(EntryTypeEnum.PROJECT)
    company: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None   # ISO month: "2024-10"
    end_date: Optional[str] = None     # ISO month or "present"
    raw_text: str = Field(..., min_length=1)
    priority: int = Field(3, ge=1, le=5)
    github_url: Optional[str] = None

    # Backward compat: accept date_range and project_type from old clients
    date_range: Optional[str] = None
    project_type: Optional[str] = None


class WorkEntryUpdate(BaseModel):
    """Schema for updating an existing work entry."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    entry_type: Optional[EntryTypeEnum] = None
    company: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    raw_text: Optional[str] = Field(None, min_length=1)
    priority: Optional[int] = Field(None, ge=1, le=5)
    github_url: Optional[str] = None

    # Backward compat
    date_range: Optional[str] = None
    project_type: Optional[str] = None


class ChunkResponse(BaseModel):
    """Schema for chunk data in API responses."""

    id: str
    chunk_text: str
    metadata_json: Optional[str] = None
    qdrant_point_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkEntryResponse(BaseModel):
    """Schema for work entry API responses."""

    id: str
    title: str
    entry_type: str
    company: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date_range: Optional[str] = None  # Computed property
    raw_text: str
    priority: int
    github_url: Optional[str] = None
    created_at: datetime
    chunk_count: int = 0

    # Backward compat alias
    project_type: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkEntryDetailResponse(WorkEntryResponse):
    """Schema for work entry with its chunks."""

    chunks: list[ChunkResponse] = []


class RepoDigestRequest(BaseModel):
    """Schema for digesting a GitHub repository."""

    github_url: str


# ---------------------------------------------------------------------------
# Backward compatibility aliases – old client code referencing these names
# will still work. Remove once frontend is fully migrated.
# ---------------------------------------------------------------------------
ProjectCreate = WorkEntryCreate
ProjectUpdate = WorkEntryUpdate
ProjectResponse = WorkEntryResponse
ProjectDetailResponse = WorkEntryDetailResponse


# ---------------------------------------------------------------------------
# UserSkill schemas
# ---------------------------------------------------------------------------

class UserSkillCreate(BaseModel):
    """Schema for creating a new user skill."""

    skill_name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1)  # language, framework, tool, infra, concept
    proficiency: str = Field("proficient")     # familiar, proficient, expert


class UserSkillUpdate(BaseModel):
    """Schema for updating an existing user skill."""

    skill_name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = None
    proficiency: Optional[str] = None


class UserSkillResponse(BaseModel):
    """Schema for user skill API responses."""

    id: int
    skill_name: str
    category: str
    proficiency: str

    model_config = {"from_attributes": True}
