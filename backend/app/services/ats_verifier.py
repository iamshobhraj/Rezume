"""ATS Verifier – Stage 5 of the resume generation pipeline.

Deterministic ATS keyword matching — no LLM needed.
Checks which JD keywords appear verbatim in the resume text and calculates
a real match ratio. If score is below threshold, provides the list of
missing high-priority keywords for a follow-up injection pass.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def calculate_ats_score(resume_text: str, jd_keywords: list[str]) -> dict:
    """Calculate a real ATS compatibility score based on keyword matching.

    Args:
        resume_text: The full text content of the generated resume
            (concatenation of all bullets, skills, titles, etc.)
        jd_keywords: List of keywords extracted from the JD by the parser.

    Returns:
        Dictionary with:
        - score: integer 0-100
        - matched: list of matched keywords
        - missing: list of all missing keywords
        - missing_high_priority: top 5 most important missing keywords
    """
    if not jd_keywords:
        return {
            "score": 100,
            "matched": [],
            "missing": [],
            "missing_high_priority": [],
        }

    resume_lower = resume_text.lower()
    matched = []
    missing = []

    for kw in jd_keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower:
            continue

        # Check for exact substring match (word-boundary aware for short keywords)
        if len(kw_lower) <= 3:
            # For short keywords like "Go", "C++", "SQL", use word boundary matching
            pattern = r'\b' + re.escape(kw_lower) + r'\b'
            if re.search(pattern, resume_lower):
                matched.append(kw)
            else:
                missing.append(kw)
        else:
            if kw_lower in resume_lower:
                matched.append(kw)
            else:
                missing.append(kw)

    total = len(matched) + len(missing)
    score = round(len(matched) / max(total, 1) * 100)

    # Missing high priority: first 5 missing keywords (they're ordered by JD position,
    # which roughly correlates with importance)
    missing_high_priority = missing[:5]

    logger.info(f"ATS score: {score}% ({len(matched)}/{total} keywords matched)")
    if missing_high_priority:
        logger.info(f"Missing high-priority: {', '.join(missing_high_priority)}")

    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "missing_high_priority": missing_high_priority,
    }


def build_resume_text(resume_data: dict) -> str:
    """Extract all text content from a resume JSON for ATS analysis.

    Concatenates all text fields: experience bullets, project bullets,
    skills, titles, etc.
    """
    parts = []

    # Experience
    for exp in resume_data.get("experience", []):
        parts.append(exp.get("title", ""))
        parts.append(exp.get("company", ""))
        parts.append(exp.get("subtitle", ""))
        for bullet in exp.get("bullets", []):
            # Strip LaTeX commands for matching
            clean = _strip_latex(bullet)
            parts.append(clean)

    # Open source
    for oss in resume_data.get("open_source", []):
        parts.append(oss.get("org_display", ""))
        for c in oss.get("contributions", []):
            parts.append(_strip_latex(c))

    # Projects
    for proj in resume_data.get("projects", []):
        parts.append(proj.get("title", ""))
        parts.append(proj.get("technologies", ""))
        for bullet in proj.get("bullets", []):
            parts.append(_strip_latex(bullet))

    # Skills
    skills = resume_data.get("skills", {})
    if isinstance(skills, dict):
        for category, skill_list in skills.items():
            if isinstance(skill_list, list):
                parts.extend(skill_list)

    return " ".join(filter(None, parts))


def _strip_latex(text: str) -> str:
    """Remove LaTeX formatting commands from text for clean matching."""
    if not text:
        return ""
    # Remove \textbf{...} → ...
    text = re.sub(r'\\textbf\{([^}]*)\}', r'\1', text)
    # Remove \textit{...} → ...
    text = re.sub(r'\\textit\{([^}]*)\}', r'\1', text)
    # Remove \href{...}{...} → second arg
    text = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', text)
    # Remove remaining backslashes before known commands
    text = text.replace("\\\\", "")
    return text
