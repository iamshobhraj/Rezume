"""Resume generation service – JD analysis, retrieval, LLM generation, and PDF rendering."""

import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.models.generated_resume import GeneratedResume
from app.models.resume_config import ResumeConfig
from app.providers.manager import ProviderManager
from app.services.pdf_service import render_pdf
from app.services.qdrant_service import qdrant_service
from app.services.ingestion import sparse_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static OSS data — never let the LLM invent these.
# Add more orgs here if you contribute elsewhere.
# ---------------------------------------------------------------------------
USER_OSS = [
    {
        "role": "Open-Source Contributor",
        "org_display": "Learning Equality (Kolibri Ecosystem)",
        "org_github": "github.com/learningequality",
        "duration": "2024 \u2013 Present",
        "contributions": [
            "Contributed across multiple Kolibri repositories focusing on developer tooling and frontend architecture.",
            "Built GitHub Actions automation for issue triage, label management, and contributor workflows.",
            "Refactored frontend notification handling by migrating state from Vuex to the Composition API.",
            "Implemented accessibility improvements (ARIA patterns, keyboard navigation); acknowledged in Kolibri 0.18.1 release notes.",
        ],
    }
]


def _format_oss_context() -> str:
    """Format USER_OSS as a numbered contribution list for the prompt."""
    lines = []
    for oss in USER_OSS:
        lines.append(f"Org: {oss['org_display']}")
        lines.append(f"GitHub: {oss['org_github']}")
        lines.append(f"Duration: {oss['duration']}")
        lines.append("Contributions (copy verbatim, do NOT paraphrase):")
        for i, c in enumerate(oss["contributions"], 1):
            lines.append(f"  [{i}] {c}")
        lines.append("")
    return "\n".join(lines)


RESUME_GENERATION_PROMPT = """You are an expert resume writer specializing in ATS-optimized resumes for engineering roles.

## Instructions
Generate a tailored resume based on the candidate's work experience, target job description, and personal info.
The resume must be ATS-safe: use standard section headings, avoid tables/columns in text, include relevant keywords from the JD.

## STRICT ONE-PAGE CONSTRAINT
The resume MUST fit on exactly ONE page. Obey these hard limits:
- Maximum 5 bullets for experience entries.
- Maximum 3 bullets per project.
- Maximum 2 OSS contributions in the open_source section.
- Skills: single line per category, no skill repeated across categories.
- If content would overflow, cut the lowest-priority project entirely.
- Do NOT include a summary/objective section — it is not in this resume format.

## Candidate Configuration
- Target Role: {target_role}
- Years of Experience: {years_experience}
- Skills Emphasis: {skills_emphasis}
- Tone: {tone}

## Candidate Personal & Education Info
{personal_info}

## Job Description
{job_description}

## Candidate Work Experience (retrieved from memory)
{retrieved_context}

## Open Source Contributions (use ONLY this data — copy contributions verbatim)
{oss_context}

## Open Source Instructions
- Include the open_source section ONLY if the contributions are relevant to the JD.
- org_display: ALWAYS use the full organization name from the list above (e.g., "Learning Equality (Kolibri Ecosystem)"). NEVER use repo names like ".github" or "kolibri-design-system".
- org_github: use the org-level link from the list above, not individual repo links.
- Pick the 2 most JD-relevant contributions from the numbered list above and copy them verbatim.
- The Kolibri 0.18.1 release notes acknowledgment is a strong signal — include it if space permits.
- If open_source is not relevant to the JD at all, return: "open_source": []

## Output Format
Respond with ONLY a valid JSON object. No markdown, no explanation, no backticks.

{{
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "date_range": "Oct 2025 \u2013 Present",
      "subtitle": "Optional one-line company descriptor e.g. FinTech / Quantitative Research Startup",
      "bullets": [
        "Achievement-oriented bullet. Use \\textbf{{KeyTerm}} to bold important technical terms."
      ]
    }}
  ],
  "open_source": [
    {{
      "role": "Open-Source Contributor",
      "org_display": "Learning Equality (Kolibri Ecosystem)",
      "org_github": "github.com/learningequality",
      "duration": "2024 \u2013 Present",
      "contributions": [
        "Copied verbatim from the numbered list above..."
      ]
    }}
  ],
  "projects": [
    {{
      "title": "Project Name",
      "technologies": "FastAPI, React, Docker, ...",
      "github_url": "https://github.com/iamshobhraj/repo",
      "gitlab_url": null,
      "live_url": null,
      "bullets": [
        "Key technical achievement relevant to the JD..."
      ]
    }}
  ],
  "skills": {{
    "languages": ["Python", "Go", "JavaScript", "TypeScript", "SQL"],
    "backend": ["FastAPI", "Flask", "Node.js"],
    "databases": ["PostgreSQL", "MongoDB", "SQLite"],
    "infra": ["Docker", "GitHub Actions", "Redis", "Git"],
    "concepts": ["System Design", "APIs", "OOP", "Event-Driven Systems"],
    "tools": ["NumPy", "SciPy", "SQLAlchemy"]
  }},
  "interests": "backend systems, distributed systems, applied AI, automation.",
  "ats_score": 85,
  "ats_notes": "Brief explanation of ATS optimization applied"
}}

Rules:
1. Skills categories must match EXACTLY: languages, backend, databases, infra, concepts, tools.
2. No skill should appear in more than one category.
3. Every project must include github_url, gitlab_url, live_url fields (null if not known).
4. Use \\textbf{{}} in bullets to bold key technical terms — this is LaTeX and renders correctly.
5. Never start a bullet with: helped, assisted, worked on, responsible for, collaborated on.
6. Bullet formula: Action verb + Technology + Impact or Scope.
7. Do NOT output name, contact, or education — those are injected from the database separately.
8. Respond ONLY with valid JSON. No extra text.
"""


class ResumeGenerationService:
    """Generates tailored resumes from job descriptions using RAG."""

    def __init__(self, db: Session, provider_manager: ProviderManager):
        self.db = db
        self.pm = provider_manager

    def generate_resume(self, job_description: str) -> GeneratedResume:
        """Generate a resume tailored to the given job description.

        Pipeline:
        1. Embed the JD
        2. Search Qdrant for relevant work chunks
        3. Load resume config + user profile
        4. Build prompt with context + JD + config + static OSS
        5. Generate structured resume JSON via LLM
        6. Post-process: overwrite personal info, education, OSS org names
        7. Render to LaTeX and compile PDF
        8. Save GeneratedResume + ResumeHistory records
        """
        resume_id = str(uuid.uuid4())

        # 1. Embed the JD
        logger.info("Embedding job description...")
        jd_vector = self.pm.embed_text(job_description)

        sparse_indices = None
        sparse_values = None
        if sparse_model:
            try:
                sparse_emb = list(sparse_model.embed([job_description]))[0]
                sparse_indices = sparse_emb.indices.tolist()
                sparse_values = sparse_emb.values.tolist()
            except Exception as e:
                logger.warning(f"Failed to generate sparse embedding for JD: {e}")

        # 2. Search Qdrant for relevant chunks
        logger.info("Searching for relevant work experience...")
        results = qdrant_service.search(
            query_vector=jd_vector,
            top_k=15,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
        )

        retrieved_context = ""
        for i, point in enumerate(results, 1):
            payload = point.payload
            score_str = (
                f" (Score: {point.score:.2f})"
                if hasattr(point, "score") and point.score
                else ""
            )
            retrieved_context += f"\n### Project/Experience {i}{score_str}\n"
            retrieved_context += (
                f"**{payload.get('title', 'N/A')}** at {payload.get('company', 'N/A')}\n"
            )
            retrieved_context += (
                f"Role: {payload.get('role', 'N/A')} | "
                f"Type: {payload.get('project_type', 'personal')} | "
                f"Priority: {payload.get('priority', 3)}/5\n"
            )
            if payload.get("summary"):
                retrieved_context += f"Summary: {payload['summary']}\n"
            if payload.get("skills"):
                retrieved_context += f"Skills: {', '.join(payload['skills'])}\n"
            if payload.get("technologies"):
                retrieved_context += f"Technologies: {', '.join(payload['technologies'])}\n"
            if payload.get("impact"):
                retrieved_context += f"Impact: {'; '.join(payload['impact'])}\n"

        if not retrieved_context.strip():
            retrieved_context = (
                "No relevant work experience found in the database. "
                "Generate a template resume using only the personal info provided."
            )

        # 3. Load resume config
        config_row = self.db.query(ResumeConfig).get("default")
        if config_row and config_row.config_json:
            try:
                config_data = json.loads(config_row.config_json)
            except json.JSONDecodeError:
                config_data = {}
        else:
            config_data = {}

        target_role = config_data.get("target_role", "Software Engineer")
        years_experience = config_data.get("years_experience", 0)
        skills_emphasis = ", ".join(config_data.get("skills_emphasis", []))
        tone = config_data.get("tone", "technical, direct")

        # 4. Load user profile
        from app.models.user_profile import UserProfile

        profile = self.db.query(UserProfile).first()
        if not profile:
            profile = UserProfile(
                name="Candidate Name",
                email="email@example.com",
                phone="",
                github="",
                linkedin="",
                location="",
                college="",
                degree="",
                graduation_year="",
                coursework="",
            )

        personal_info_str = (
            f"Name: {profile.name}\n"
            f"Email: {profile.email}\n"
            f"Phone: {profile.phone or 'N/A'}\n"
            f"GitHub: {profile.github or 'N/A'}\n"
            f"LinkedIn: {profile.linkedin or 'N/A'}\n"
            f"Location: {profile.location or 'N/A'}\n"
            f"College: {profile.college or 'N/A'}\n"
            f"Degree: {profile.degree or 'N/A'}\n"
            f"Graduation Year: {profile.graduation_year or 'N/A'}\n"
            f"Coursework: {profile.coursework or 'N/A'}"
        )

        # 5. Build prompt and call LLM
        prompt = RESUME_GENERATION_PROMPT.format(
            target_role=target_role,
            years_experience=years_experience,
            skills_emphasis=skills_emphasis or "No specific emphasis",
            tone=tone,
            job_description=job_description,
            retrieved_context=retrieved_context,
            personal_info=personal_info_str,
            oss_context=_format_oss_context(),
        )

        logger.info("Generating resume content via LLM...")
        response = self.pm.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4096,
        )

        # 6. Parse JSON — strip markdown fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            cleaned = "\n".join(lines[1:end]).strip()

        try:
            resume_data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            resume_data = {"error": "Failed to parse LLM response", "raw": cleaned}

        # 7. Post-process
        if isinstance(resume_data, dict) and "error" not in resume_data:

            # Personal info — always from DB, never from LLM
            resume_data["name"] = profile.name
            resume_data["contact"] = {
                "email": profile.email,
                "phone": profile.phone or "",
                "github": profile.github or "",
                "linkedin": profile.linkedin or "",
                "location": profile.location or "",
            }
            # Flat copies for Jinja2 template convenience
            resume_data["email"] = profile.email
            resume_data["phone"] = profile.phone or ""
            resume_data["github"] = profile.github or ""
            resume_data["linkedin"] = profile.linkedin or ""
            resume_data["location"] = profile.location or ""

            # Education — always from DB
            if profile.college or profile.degree:
                resume_data["education"] = [
                    {
                        "institution": profile.college or "",
                        "degree": profile.degree or "",
                        "year": profile.graduation_year or "",
                        "coursework": profile.coursework or "",
                    }
                ]

            # OSS — correct org metadata from static data; validate contributions
            if resume_data.get("open_source"):
                corrected = []
                for entry in resume_data["open_source"]:
                    static = _find_matching_oss(entry)
                    if static:
                        entry["role"] = static["role"]
                        entry["org_display"] = static["org_display"]
                        entry["org_github"] = static["org_github"]
                        entry["duration"] = static["duration"]
                        valid = _validate_contributions(
                            entry.get("contributions", []),
                            static["contributions"],
                        )
                        # Fall back to first 2 real contributions if LLM hallucinated
                        entry["contributions"] = valid or static["contributions"][:2]
                    corrected.append(entry)
                resume_data["open_source"] = corrected

            # Skills — ensure all expected keys exist
            expected_skill_keys = [
                "languages", "backend", "databases", "infra", "concepts", "tools"
            ]
            skills = resume_data.get("skills", {})
            if isinstance(skills, dict):
                for key in expected_skill_keys:
                    skills.setdefault(key, [])
                resume_data["skills"] = skills

            # Projects — ensure url fields always present
            for proj in resume_data.get("projects", []):
                proj.setdefault("github_url", None)
                proj.setdefault("gitlab_url", None)
                proj.setdefault("live_url", None)

        # 8. Render PDF
        latex_content = None
        pdf_path = None
        try:
            from app.services.pdf_service import render_resume_to_latex

            latex_content = render_resume_to_latex(resume_data, profile=profile)
            pdf_path = render_pdf(latex_content)
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")

        # 9. Save records
        from app.models.resume_history import ResumeHistory

        score = resume_data.get("ats_score") if isinstance(resume_data, dict) else None
        resume = GeneratedResume(
            id=resume_id,
            job_description=job_description,
            generated_content=json.dumps(resume_data, indent=2),
            generated_latex=latex_content,
            pdf_path=pdf_path,
            score=float(score) if score else None,
        )
        self.db.add(resume)

        history = ResumeHistory(
            id=str(uuid.uuid4()),
            generated_resume_id=resume_id,
            tags="Auto-generated",
            resume_json=json.dumps(resume_data),
        )
        self.db.add(history)

        self.db.commit()
        logger.info(f"Generated resume {resume_id} (ATS score: {score})")
        return resume


# ---------------------------------------------------------------------------
# OSS helpers
# ---------------------------------------------------------------------------

def _find_matching_oss(oss_entry: dict) -> dict | None:
    """Find the matching static USER_OSS entry for an LLM-generated OSS entry."""
    org = (
        oss_entry.get("org_display") or oss_entry.get("org") or ""
    ).lower()
    for static in USER_OSS:
        if (
            "learning equality" in org
            or "kolibri" in org
            or "learningequality" in org
        ):
            return static
    return None


def _validate_contributions(
    llm_contributions: list[str], real_contributions: list[str]
) -> list[str]:
    """Keep only LLM contributions that are close to real ones.

    Accepts verbatim copies and near-verbatim paraphrases (>60% word overlap).
    Returns the canonical real-contribution text for accepted entries.
    """
    validated = []
    for llm_c in llm_contributions:
        llm_lower = llm_c.lower().strip()
        for real_c in real_contributions:
            real_lower = real_c.lower().strip()
            # Verbatim check — first 40 chars match
            if llm_lower[:40] == real_lower[:40]:
                validated.append(real_c)
                break
            # Word-overlap check
            llm_words = set(llm_lower.split())
            real_words = set(real_lower.split())
            if len(llm_words & real_words) / max(len(real_words), 1) > 0.6:
                validated.append(real_c)
                break
    return validated
