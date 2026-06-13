"""Per-Entry Bullet Generator – Stage 4 of the resume generation pipeline.

Generates 3 achievement-oriented resume bullets per work entry using a focused
LLM call. Each call receives only the context for one entry + JD keywords +
skill framing hints, producing dramatically better bullets than the monolithic approach.
"""

import json
import logging
from typing import Optional

from app.providers.manager import ProviderManager
from app.services.retrieval import RetrievedEntry

logger = logging.getLogger(__name__)


BULLET_GEN_PROMPT = """Write {num_bullets} resume bullets for this experience entry.
The bullets are for a resume targeting this role: {target_role}

Entry details:
- Title: {title}
- Company: {company}
- Duration: {date_range}
- What was built: {summary}
- Technologies used: {technologies}
- Impact / metrics: {impact}

JD keywords to naturally include (at least 2): {ats_keywords}

{framing_section}

Rules:
- Start every bullet with a strong action verb (Engineered, Architected, Deployed, Optimized, Built, etc.)
- Formula: Action verb + Technology + Quantified impact or scope
- Bold critical technical terms with \\textbf{{}} (this is LaTeX)
- NEVER start with: helped, assisted, worked on, responsible for, collaborated on, utilized
- Include at least 2 of the JD keywords listed above
- Each bullet should be 1-2 lines max
- Quantify where possible (percentage improvements, scale, user counts, latency reductions)
- If no specific metrics are available, quantify scope (e.g., "serving 10K+ requests/day")

Return ONLY a JSON array of {num_bullets} strings. No markdown, no explanation.
Example: ["Engineered a \\\\textbf{{FastAPI}} service...", "Deployed \\\\textbf{{Docker}} containers..."]
"""


SKILLS_SECTION_PROMPT = """Generate the skills section for this resume.

Target role: {target_role}
JD required skills: {required_skills}
JD nice-to-have: {nice_to_have_skills}
Candidate's actual skills: {user_skills}
Skills used across selected entries: {entry_skills}

Skill bridge analysis:
- Matched: {matched_skills}
- Adjacent (include these): {adjacent_skills}

Return ONLY valid JSON with these exact keys. Each value is a list of strings.
Only include skills the candidate actually has or that are legitimately adjacent.
Never include skills from the "gaps" list.

{{
  "languages": ["Python", "JavaScript", ...],
  "backend": ["FastAPI", "Node.js", ...],
  "databases": ["PostgreSQL", "Redis", ...],
  "infra": ["Docker", "GitHub Actions", ...],
  "concepts": ["System Design", "REST APIs", ...],
  "tools": ["NumPy", "SQLAlchemy", ...]
}}

Rules:
- Prioritize skills that match the JD
- No skill should appear in more than one category
- Each category should have 3-6 items max
- Return ONLY valid JSON
"""


class BulletGenerator:
    """Generates achievement-oriented resume bullets per entry."""

    def __init__(self, provider_manager: ProviderManager):
        self.pm = provider_manager

    def generate_bullets(
        self,
        entry: RetrievedEntry,
        target_role: str,
        ats_keywords: list[str],
        framing_hints: Optional[dict] = None,
        num_bullets: int = 3,
        date_range: str = "",
    ) -> list[str]:
        """Generate resume bullets for a single entry.

        Args:
            entry: The retrieved work entry context.
            target_role: The target role from JD.
            ats_keywords: Keywords to include for ATS optimization.
            framing_hints: Adjacent skill framing from skill bridge.
            num_bullets: Number of bullets to generate (2-5).
            date_range: Date range string for this entry.

        Returns:
            List of bullet strings with LaTeX formatting.
        """
        # Build framing section if we have adjacent skill hints
        framing_section = ""
        if framing_hints:
            framing_lines = ["Skill framing guidance (use these framings when applicable):"]
            for jd_skill, framing in framing_hints.items():
                framing_lines.append(f"  - For \"{jd_skill}\": {framing}")
            framing_section = "\n".join(framing_lines)

        technologies = ", ".join(
            list(set(entry.skills + entry.technologies))[:15]
        ) or "Not specified"

        impact = "; ".join(entry.impact[:5]) or "No specific metrics available"

        prompt = BULLET_GEN_PROMPT.format(
            num_bullets=num_bullets,
            target_role=target_role,
            title=entry.title,
            company=entry.company or "N/A",
            date_range=date_range or "N/A",
            summary=entry.project_summary or f"Project: {entry.title}",
            technologies=technologies,
            impact=impact,
            ats_keywords=", ".join(ats_keywords[:10]) or "general software engineering terms",
            framing_section=framing_section,
        )

        try:
            response = self.pm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
            )

            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                end = -1 if lines[-1].strip() == "```" else len(lines)
                cleaned = "\n".join(lines[1:end]).strip()

            bullets = json.loads(cleaned)
            if isinstance(bullets, list) and len(bullets) > 0:
                logger.info(f"Generated {len(bullets)} bullets for '{entry.title}'")
                return bullets[:num_bullets]
            else:
                logger.warning(f"Unexpected bullet format for '{entry.title}': {type(bullets)}")
                return self._fallback_bullets(entry, num_bullets)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse bullets JSON for '{entry.title}': {e}")
            return self._fallback_bullets(entry, num_bullets)

        except Exception as e:
            logger.error(f"Bullet generation failed for '{entry.title}': {e}")
            return self._fallback_bullets(entry, num_bullets)

    def generate_skills_section(
        self,
        target_role: str,
        required_skills: list[str],
        nice_to_have_skills: list[str],
        user_skills_str: str,
        entry_skills: list[str],
        matched_skills: dict,
        adjacent_skills: dict,
    ) -> dict:
        """Generate the skills section of the resume.

        Returns a dict with keys: languages, backend, databases, infra, concepts, tools.
        """
        prompt = SKILLS_SECTION_PROMPT.format(
            target_role=target_role,
            required_skills=", ".join(required_skills) or "general",
            nice_to_have_skills=", ".join(nice_to_have_skills) or "none",
            user_skills=user_skills_str or "Not specified",
            entry_skills=", ".join(list(set(entry_skills))[:30]) or "Not specified",
            matched_skills=json.dumps(matched_skills) if matched_skills else "{}",
            adjacent_skills=json.dumps(adjacent_skills) if adjacent_skills else "{}",
        )

        try:
            response = self.pm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=512,
            )

            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                end = -1 if lines[-1].strip() == "```" else len(lines)
                cleaned = "\n".join(lines[1:end]).strip()

            skills = json.loads(cleaned)

            # Ensure all expected keys exist
            expected_keys = ["languages", "backend", "databases", "infra", "concepts", "tools"]
            for key in expected_keys:
                skills.setdefault(key, [])

            return skills

        except Exception as e:
            logger.error(f"Skills section generation failed: {e}")
            return {
                "languages": [], "backend": [], "databases": [],
                "infra": [], "concepts": [], "tools": [],
            }

    def _fallback_bullets(self, entry: RetrievedEntry, num_bullets: int) -> list[str]:
        """Generate simple fallback bullets from entry metadata."""
        bullets = []
        if entry.project_summary:
            bullets.append(f"Developed {entry.title} — {entry.project_summary[:150]}")
        if entry.technologies:
            tech_str = ", ".join(entry.technologies[:5])
            bullets.append(f"Built using {tech_str}")
        if entry.impact:
            bullets.append(entry.impact[0])

        # Pad to requested count
        while len(bullets) < num_bullets:
            bullets.append(f"Contributed to {entry.title} project development and delivery")

        return bullets[:num_bullets]
