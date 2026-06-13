"""ORM models package – import all models here so Base.metadata sees them."""

from app.models.llm_provider import LLMProvider
from app.models.work_entry import WorkEntry, Chunk, EntryType
from app.models.user_skill import UserSkill
from app.models.resume_config import ResumeConfig
from app.models.generated_resume import GeneratedResume
from app.models.github_user import GithubUser
from app.models.resume_history import ResumeHistory
from app.models.user_profile import UserProfile
from app.models.jd_cache import JDCache

# Backward compatibility alias – code that still references "Project"
# will continue to work during the migration period.
Project = WorkEntry

__all__ = [
    "LLMProvider",
    "WorkEntry",
    "Project",  # alias
    "Chunk",
    "EntryType",
    "UserSkill",
    "ResumeConfig",
    "GeneratedResume",
    "GithubUser",
    "ResumeHistory",
    "UserProfile",
    "JDCache",
]
