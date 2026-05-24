"""Pydantic schemas for UserProfile operations."""

from typing import Optional

from pydantic import BaseModel


class UserProfileBase(BaseModel):
    """Base fields for UserProfile."""

    name: str
    email: str
    phone: Optional[str] = ""
    github: Optional[str] = ""
    linkedin: Optional[str] = ""
    portfolio: Optional[str] = ""
    location: Optional[str] = ""
    college: Optional[str] = ""
    college_start_year: Optional[str] = ""
    degree: Optional[str] = ""
    graduation_year: Optional[str] = ""
    coursework: Optional[str] = ""


class UserProfileUpdate(UserProfileBase):
    """Schema for updating a user profile."""

    pass


class UserProfileResponse(UserProfileBase):
    """Schema for returning a user profile."""

    id: int

    class Config:
        from_attributes = True
