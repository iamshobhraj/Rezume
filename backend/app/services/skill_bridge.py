"""Skill Bridge Analyzer – Stage 2 of the resume generation pipeline.

Compares JD required skills against the candidate's UserSkill inventory to identify:
- Direct matches (candidate has the exact skill)
- Adjacent skills (candidate has a related skill — provides honest framing)
- Gaps (candidate doesn't have this — omit from resume)
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user_skill import UserSkill
from app.providers.manager import ProviderManager

logger = logging.getLogger(__name__)


SKILL_BRIDGE_PROMPT = """You are a resume skills advisor. Analyze how a candidate's skills map to job requirements.

JD requires these skills: {required_skills}
JD nice-to-have: {nice_to_have_skills}

Candidate has these skills (with proficiency):
{user_skills}

For each required skill, determine:
1. EXACT MATCH: candidate has this skill or a very close variant (e.g., "PostgreSQL" matches "Postgres")
2. ADJACENT: candidate has a related skill that can be honestly framed. Provide the framing.
   Example: Candidate has "Docker + AWS ECS" → JD wants "Kubernetes" → Frame as "orchestrated containerized services across cloud infrastructure"
3. GAP: candidate doesn't have this skill or anything related — must be omitted

Return ONLY valid JSON:
{{
  "matched": {{"skill_name": "direct match"}},
  "adjacent": {{"jd_skill": "Honest framing using candidate's actual skills: ..."}},
  "gaps": ["skill_a", "skill_b"]
}}

Rules:
- NEVER fabricate experience. Adjacent framing must use skills the candidate actually has.
- Be generous with matches — "React" and "React.js" are the same, "Postgres" and "PostgreSQL" are the same.
- For adjacent skills, the framing should be a short phrase a resume bullet could use.
- Return ONLY valid JSON.
"""


class SkillBridge:
    """Result of skill bridge analysis."""

    def __init__(self, data: dict):
        self.matched: dict[str, str] = data.get("matched", {})
        self.adjacent: dict[str, str] = data.get("adjacent", {})
        self.gaps: list[str] = data.get("gaps", [])
        self._raw = data

    @property
    def covered_skills(self) -> list[str]:
        """All skills that are either matched or have an adjacent framing."""
        return list(self.matched.keys()) + list(self.adjacent.keys())

    def get_framing(self, skill: str) -> Optional[str]:
        """Get the framing hint for a skill (either direct or adjacent)."""
        if skill in self.matched:
            return None  # No framing needed for direct matches
        return self.adjacent.get(skill)

    def to_dict(self) -> dict:
        return self._raw


class SkillBridgeAnalyzer:
    """Analyzes skill gaps between JD requirements and candidate inventory."""

    def __init__(self, db: Session, provider_manager: ProviderManager):
        self.db = db
        self.pm = provider_manager

    def _get_user_skills(self) -> list[UserSkill]:
        """Fetch all user skills from the database."""
        return self.db.query(UserSkill).all()

    def _format_user_skills(self, skills: list[UserSkill]) -> str:
        """Format user skills for the prompt."""
        if not skills:
            return "No skills recorded in inventory."

        lines = []
        by_category: dict[str, list[UserSkill]] = {}
        for s in skills:
            by_category.setdefault(s.category, []).append(s)

        for category, cat_skills in sorted(by_category.items()):
            skill_strs = [f"{s.skill_name} ({s.proficiency})" for s in cat_skills]
            lines.append(f"  {category}: {', '.join(skill_strs)}")

        return "\n".join(lines)

    def analyze(
        self,
        required_skills: list[str],
        nice_to_have_skills: list[str],
    ) -> SkillBridge:
        """Analyze skill gaps and generate framing guidance.

        Args:
            required_skills: Skills explicitly required by the JD.
            nice_to_have_skills: Nice-to-have skills from the JD.

        Returns:
            SkillBridge with matched, adjacent, and gap categorizations.
        """
        user_skills = self._get_user_skills()

        if not user_skills:
            logger.warning("No user skills in inventory — skill bridge analysis skipped")
            return SkillBridge({
                "matched": {},
                "adjacent": {},
                "gaps": required_skills,
            })

        if not required_skills and not nice_to_have_skills:
            logger.info("No JD skills to analyze — skill bridge skipped")
            return SkillBridge({"matched": {}, "adjacent": {}, "gaps": []})

        logger.info(f"Analyzing skill bridge (Stage 2): "
                     f"{len(required_skills)} required, {len(user_skills)} candidate skills")

        try:
            prompt = SKILL_BRIDGE_PROMPT.format(
                required_skills=", ".join(required_skills),
                nice_to_have_skills=", ".join(nice_to_have_skills) or "None",
                user_skills=self._format_user_skills(user_skills),
            )

            response = self.pm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
            )

            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                end = -1 if lines[-1].strip() == "```" else len(lines)
                cleaned = "\n".join(lines[1:end]).strip()

            data = json.loads(cleaned)
            bridge = SkillBridge(data)

            logger.info(f"Skill bridge: {len(bridge.matched)} matched, "
                        f"{len(bridge.adjacent)} adjacent, {len(bridge.gaps)} gaps")
            return bridge

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse skill bridge response: {e}")
            # Fallback: do a simple string-matching approach
            return self._simple_match(required_skills, user_skills)

        except Exception as e:
            logger.error(f"Skill bridge analysis failed: {e}")
            return self._simple_match(required_skills, user_skills)

    def _simple_match(self, required: list[str], user_skills: list[UserSkill]) -> SkillBridge:
        """Fallback: simple case-insensitive string matching."""
        user_names = {s.skill_name.lower(): s.skill_name for s in user_skills}
        matched = {}
        gaps = []

        for req in required:
            req_lower = req.lower()
            if req_lower in user_names:
                matched[req] = "direct"
            else:
                # Check for partial matches
                found = False
                for user_lower, user_name in user_names.items():
                    if req_lower in user_lower or user_lower in req_lower:
                        matched[req] = f"matched via {user_name}"
                        found = True
                        break
                if not found:
                    gaps.append(req)

        return SkillBridge({"matched": matched, "adjacent": {}, "gaps": gaps})
