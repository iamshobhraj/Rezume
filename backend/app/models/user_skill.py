"""UserSkill ORM model – structured skill inventory for the candidate.

Feeds the skill bridge analysis during resume generation:
- Each skill has a category (language, framework, tool, infra, concept)
- Proficiency level (familiar, proficient, expert) weights how prominently
  the skill is featured in the generated resume.
"""

from sqlalchemy import Column, Integer, String

from app.database import Base


class UserSkill(Base):
    """A skill the candidate possesses, with category and proficiency."""

    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String, nullable=False)
    category = Column(String, nullable=False)      # language, framework, tool, infra, concept
    proficiency = Column(String, default="proficient")  # familiar, proficient, expert
