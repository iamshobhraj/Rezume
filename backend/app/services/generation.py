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

RESUME_GENERATION_PROMPT = """You are an expert resume writer specializing in ATS-optimized resumes for engineering roles.

## Instructions
Generate a tailored resume based on the candidate's work experience and the target job description.
The resume must be ATS-safe: use standard section headings, avoid tables/columns in text, include relevant keywords from the JD.

## Candidate Configuration
- Target Role: {target_role}
- Years of Experience: {years_experience}
- Skills Emphasis: {skills_emphasis}
- Tone: {tone}

## Job Description
{job_description}

## Relevant Work Experience (retrieved from candidate's history)
{retrieved_context}

## Output Format
Respond with a JSON object containing:
{{
  "name": "Candidate Name (placeholder)",
  "contact": {{
    "email": "email@example.com",
    "phone": "(555) 000-0000",
    "linkedin": "linkedin.com/in/candidate",
    "location": "City, State"
  }},
  "summary": "2-3 sentence professional summary tailored to the JD",
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "date_range": "Start - End",
      "bullets": ["Achievement-oriented bullet point with metrics..."]
    }}
  ],
  "projects": [
    {{
      "title": "Project Name (OSS or Personal)",
      "technologies": "Tech stack used",
      "date_range": "Date or Year",
      "bullets": ["Key technical achievements..."]
    }}
  ],
  "skills": {{
    "languages": ["Python", "Go", ...],
    "frameworks": ["FastAPI", "React", ...],
    "tools": ["Docker", "Kubernetes", ...],
    "other": ["System Design", ...]
  }},
  "education": [
    {{
      "degree": "Degree Name",
      "institution": "University",
      "year": "Year"
    }}
  ],
  "ats_score": 85,
  "ats_notes": "Brief explanation of ATS optimization applied"
}}

Respond ONLY with valid JSON.
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
        3. Load resume config preferences
        4. Build prompt with context + JD + config
        5. Generate structured resume via LLM
        6. Render to LaTeX and compile PDF
        7. Save and return GeneratedResume record

        Args:
            job_description: The full job description text.

        Returns:
            The saved GeneratedResume record.
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

        # 2. Search for relevant chunks
        logger.info("Searching for relevant work experience...")
        results = qdrant_service.search(
            query_vector=jd_vector, 
            top_k=15,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values
        )

        # Build context from retrieved chunks
        retrieved_context = ""
        for i, point in enumerate(results, 1):
            payload = point.payload
            score_str = f" (Score: {point.score:.2f})" if hasattr(point, 'score') and point.score else ""
            retrieved_context += f"\n### Project/Experience {i}{score_str}\n"
            retrieved_context += f"**{payload.get('title', 'N/A')}** at {payload.get('company', 'N/A')}\n"
            retrieved_context += f"Role: {payload.get('role', 'N/A')} | Type: {payload.get('project_type', 'personal')} | Priority: {payload.get('priority', 3)}/5\n"
            if payload.get("summary"):
                retrieved_context += f"Summary: {payload['summary']}\n"
            if payload.get("skills"):
                retrieved_context += f"Skills: {', '.join(payload['skills'])}\n"
            if payload.get("technologies"):
                retrieved_context += f"Technologies: {', '.join(payload['technologies'])}\n"
            if payload.get("impact"):
                retrieved_context += f"Impact: {'; '.join(payload['impact'])}\n"

        if not retrieved_context.strip():
            retrieved_context = "No relevant work experience found in the database. Generate a template resume."

        # 3. Load config
        config_row = self.db.query(ResumeConfig).get("default")
        if config_row and config_row.config_json:
            try:
                config_data = json.loads(config_row.config_json)
            except json.JSONDecodeError:
                config_data = {}
        else:
            config_data = {}

        target_role = config_data.get("target_role", "Software Engineer")
        years_experience = config_data.get("years_experience", 5)
        skills_emphasis = ", ".join(config_data.get("skills_emphasis", []))
        tone = config_data.get("tone", "professional")

        # 4. Build prompt
        prompt = RESUME_GENERATION_PROMPT.format(
            target_role=target_role,
            years_experience=years_experience,
            skills_emphasis=skills_emphasis or "No specific emphasis",
            tone=tone,
            job_description=job_description,
            retrieved_context=retrieved_context,
        )

        # 5. Generate resume via LLM
        logger.info("Generating resume content via LLM...")
        response = self.pm.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4096,
        )

        # Parse the JSON response
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            resume_data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            resume_data = {"error": "Failed to parse LLM response", "raw": cleaned}

        # 6. Render PDF
        latex_content = None
        pdf_path = None
        try:
            from app.services.pdf_service import render_resume_to_latex
            latex_content = render_resume_to_latex(resume_data)
            pdf_path = render_pdf(latex_content)
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")

        # 7. Save record
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
        
        # 8. Save history record
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

