"""JD Parser – Stage 1 of the resume generation pipeline.

Extracts structured fields from a raw job description using a focused LLM prompt.
Results are cached by JD text hash to avoid redundant parsing.
"""

import hashlib
import json
import logging
from typing import Optional

from app.providers.manager import ProviderManager
from app.models.jd_cache import JDCache
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# In-memory cache for JD parse results (keyed by SHA-256 of JD text)
_jd_cache: dict[str, dict] = {}


JD_PARSE_PROMPT = """Extract structured information from this job description.
Return ONLY valid JSON with these exact keys:

{
  "role_title": "exact job title from the posting",
  "seniority": "junior|mid|senior|lead|staff|principal",
  "company_name": "company name if mentioned",
  "required_skills": ["skill1", "skill2"],
  "nice_to_have_skills": ["skill1", "skill2"],
  "key_responsibilities": ["responsibility1", "responsibility2"],
  "domain_keywords": ["fintech", "real-time", "e-commerce"],
  "ats_keywords": ["exact keywords an ATS system would match, including technologies, methodologies, and domain terms"]
}

Rules:
- required_skills: technologies, languages, frameworks explicitly required
- nice_to_have_skills: skills listed as "preferred", "bonus", "nice to have"
- ats_keywords: comprehensive list of ALL technical terms, tools, methodologies, and domain words that an ATS would scan for
- Be exhaustive with ats_keywords — include every technology, framework, protocol, and methodology mentioned
- Return ONLY valid JSON. No markdown, no explanation.

Job Description:
{jd_text}
"""


class ParsedJD:
    """Structured representation of a parsed job description."""

    def __init__(self, data: dict):
        self.role_title: str = data.get("role_title", "Software Engineer")
        self.seniority: str = data.get("seniority", "mid")
        self.company_name: str = data.get("company_name", "")
        self.required_skills: list[str] = data.get("required_skills", [])
        self.nice_to_have_skills: list[str] = data.get("nice_to_have_skills", [])
        self.key_responsibilities: list[str] = data.get("key_responsibilities", [])
        self.domain_keywords: list[str] = data.get("domain_keywords", [])
        self.ats_keywords: list[str] = data.get("ats_keywords", [])
        self._raw = data

    @property
    def all_skills(self) -> list[str]:
        """Combined required + nice-to-have skills."""
        return self.required_skills + self.nice_to_have_skills

    def to_dict(self) -> dict:
        return self._raw


class JDParser:
    """Parses raw job descriptions into structured data."""

    def __init__(self, db: Session, provider_manager: ProviderManager):
        self.db = db
        self.pm = provider_manager

    def parse(self, jd_text: str) -> ParsedJD:
        """Parse a job description into structured fields.

        Uses database cache to avoid re-parsing the same JD.
        """
        cache_key = hashlib.sha256(jd_text.encode()).hexdigest()

        # Check memory cache first
        if cache_key in _jd_cache:
            logger.info("JD parse in-memory cache hit")
            return ParsedJD(_jd_cache[cache_key])
            
        # Check DB cache
        try:
            db_cache = self.db.query(JDCache).filter(JDCache.jd_hash == cache_key).first()
            if db_cache:
                logger.info("JD parse database cache hit")
                data = json.loads(db_cache.parsed_json)
                _jd_cache[cache_key] = data  # populate memory cache
                return ParsedJD(data)
        except Exception as e:
            logger.warning(f"Failed to read from JD database cache: {e}")

        logger.info("Parsing job description (Stage 1)...")

        try:
            response = self.pm.generate(
                messages=[{"role": "user", "content": JD_PARSE_PROMPT.format(jd_text=jd_text)}],
                temperature=0.1,
                max_tokens=1024,
            )

            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                end = -1 if lines[-1].strip() == "```" else len(lines)
                cleaned = "\n".join(lines[1:end]).strip()

            data = json.loads(cleaned)
            _jd_cache[cache_key] = data
            
            # Save to DB cache
            try:
                new_cache = JDCache(jd_hash=cache_key, parsed_json=json.dumps(data))
                self.db.add(new_cache)
                self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to save to JD database cache: {e}")
                self.db.rollback()
                
            logger.info(f"JD parsed: role={data.get('role_title')}, "
                        f"{len(data.get('required_skills', []))} required skills, "
                        f"{len(data.get('ats_keywords', []))} ATS keywords")
            return ParsedJD(data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JD parser response as JSON: {e}")
            # Return a minimal parsed JD with the raw text as context
            fallback = {
                "role_title": "Software Engineer",
                "seniority": "mid",
                "required_skills": [],
                "nice_to_have_skills": [],
                "key_responsibilities": [],
                "domain_keywords": [],
                "ats_keywords": [],
            }
            return ParsedJD(fallback)

        except Exception as e:
            logger.error(f"JD parsing failed: {e}")
            return ParsedJD({})
