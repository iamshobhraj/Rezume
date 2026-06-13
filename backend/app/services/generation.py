"""Resume generation service – multi-stage pipeline orchestrator.

Replaces the old monolithic single-shot approach with a 6-stage pipeline:
1. JD Parser → structured JD fields
2. Skill Bridge → match/adjacent/gap analysis
3. Typed Retrieval → separate context per section with MMR
4. Per-Entry Bullet Generator → focused, achievement-oriented bullets
5. ATS Verification → deterministic keyword scoring
6. PDF Rendering → LaTeX compilation
"""

import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.models.generated_resume import GeneratedResume
from app.models.resume_config import ResumeConfig
from app.models.user_skill import UserSkill
from app.providers.manager import ProviderManager
from app.services.ats_verifier import build_resume_text, calculate_ats_score
from app.services.bullet_generator import BulletGenerator
from app.services.jd_parser import JDParser
from app.services.pdf_service import render_pdf
from app.services.qdrant_service import qdrant_service
from app.services.retrieval import RetrievedEntry, TypedRetriever
from app.services.skill_bridge import SkillBridgeAnalyzer
from app.services.ingestion import sparse_model

logger = logging.getLogger(__name__)


class ResumeGenerationService:
    """Generates tailored resumes from job descriptions using a multi-stage RAG pipeline."""

    def __init__(self, db: Session, provider_manager: ProviderManager):
        self.db = db
        self.pm = provider_manager

    def generate_resume(self, job_description: str) -> GeneratedResume:
        """Generate a resume tailored to the given job description.

        Multi-stage pipeline:
        1. Parse JD → structured fields (role, skills, keywords)
        2. Skill bridge → match candidate skills against JD requirements
        3. Typed retrieval → fetch relevant work entries per section
        4. Bullet generation → focused LLM calls per entry
        5. ATS verification → deterministic keyword scoring
        6. Assemble JSON → render LaTeX → compile PDF
        """
        resume_id = str(uuid.uuid4())

        # ── Stage 1: Parse JD ──────────────────────────────────────────
        jd_parser = JDParser(self.db, self.pm)
        parsed_jd = jd_parser.parse(job_description)
        logger.info(f"Stage 1 complete: role={parsed_jd.role_title}, "
                     f"{len(parsed_jd.ats_keywords)} ATS keywords")

        # ── Stage 2: Skill Bridge Analysis ─────────────────────────────
        skill_bridge_analyzer = SkillBridgeAnalyzer(self.db, self.pm)
        skill_bridge = skill_bridge_analyzer.analyze(
            required_skills=parsed_jd.required_skills,
            nice_to_have_skills=parsed_jd.nice_to_have_skills,
        )
        logger.info(f"Stage 2 complete: {len(skill_bridge.matched)} matched, "
                     f"{len(skill_bridge.adjacent)} adjacent, {len(skill_bridge.gaps)} gaps")

        # ── Stage 3: Typed Retrieval ───────────────────────────────────
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

        retriever = TypedRetriever()
        retrieval_result = retriever.retrieve(
            query_vector=jd_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
        )
        logger.info(f"Stage 3 complete: {retrieval_result.total_count} entries "
                     f"(work={len(retrieval_result.work_entries)}, "
                     f"proj={len(retrieval_result.project_entries)}, "
                     f"oss={len(retrieval_result.oss_entries)})")

        # ── Load config + profile ──────────────────────────────────────
        config_row = self.db.query(ResumeConfig).get("default")
        if config_row and config_row.config_json:
            try:
                config_data = json.loads(config_row.config_json)
            except json.JSONDecodeError:
                config_data = {}
        else:
            config_data = {}

        target_role = parsed_jd.role_title or config_data.get("target_role", "Software Engineer")

        from app.models.user_profile import UserProfile
        profile = self.db.query(UserProfile).first()
        if not profile:
            profile = UserProfile(
                name="Candidate Name", email="email@example.com",
                phone="", github="", linkedin="", location="",
                college="", degree="", graduation_year="", coursework="",
            )

        # ── Stage 4: Per-Entry Bullet Generation ───────────────────────
        bullet_gen = BulletGenerator(self.pm)

        # Get user skills for skills section
        user_skills = self.db.query(UserSkill).all()
        user_skills_str = ", ".join([f"{s.skill_name} ({s.category})" for s in user_skills])

        # Generate experience section (from work entries)
        experience_entries = []
        all_entry_skills = []
        for entry in retrieval_result.work_entries:
            try:
                bullets = bullet_gen.generate_bullets(
                    entry=entry,
                    target_role=target_role,
                    ats_keywords=parsed_jd.ats_keywords[:10],
                    framing_hints=skill_bridge.adjacent,
                    num_bullets=4 if entry.priority >= 4 else 3,
                    date_range=entry.title,  # Will be replaced by actual dates if available
                )
                experience_entries.append({
                    "title": entry.role or target_role,
                    "company": entry.company or entry.title,
                    "date_range": "",  # Will be populated from DB if available
                    "subtitle": entry.domain or "",
                    "bullets": bullets,
                    "_work_entry_id": entry.work_entry_id,
                })
                all_entry_skills.extend(entry.skills + entry.technologies)
            except Exception as e:
                logger.warning(f"Bullet generation failed for '{entry.title}': {e}")
                continue

        # Generate project section (from personal projects)
        project_entries = []
        for entry in retrieval_result.project_entries:
            try:
                bullets = bullet_gen.generate_bullets(
                    entry=entry,
                    target_role=target_role,
                    ats_keywords=parsed_jd.ats_keywords[:8],
                    framing_hints=skill_bridge.adjacent,
                    num_bullets=3,
                )
                proj_data = {
                    "title": entry.title,
                    "technologies": ", ".join(list(set(entry.skills + entry.technologies))[:8]),
                    "github_url": None,
                    "gitlab_url": None,
                    "live_url": None,
                    "bullets": bullets,
                }
                project_entries.append(proj_data)
                all_entry_skills.extend(entry.skills + entry.technologies)
            except Exception as e:
                logger.warning(f"Bullet generation failed for project '{entry.title}': {e}")
                continue

        # Generate OSS section (from OSS entries)
        oss_entries = []
        for entry in retrieval_result.oss_entries:
            try:
                bullets = bullet_gen.generate_bullets(
                    entry=entry,
                    target_role=target_role,
                    ats_keywords=parsed_jd.ats_keywords[:6],
                    framing_hints=skill_bridge.adjacent,
                    num_bullets=2,
                )
                oss_entries.append({
                    "role": entry.role or "Open-Source Contributor",
                    "org_display": entry.company or entry.title,
                    "org_github": "",  # Will be enriched from DB
                    "duration": "",
                    "contributions": bullets,
                    "_work_entry_id": entry.work_entry_id,
                })
                all_entry_skills.extend(entry.skills + entry.technologies)
            except Exception as e:
                logger.warning(f"Bullet generation failed for OSS '{entry.title}': {e}")
                continue

        logger.info(f"Stage 4 complete: {len(experience_entries)} experiences, "
                     f"{len(project_entries)} projects, {len(oss_entries)} OSS")

        # ── Generate Skills Section ────────────────────────────────────
        skills_section = bullet_gen.generate_skills_section(
            target_role=target_role,
            required_skills=parsed_jd.required_skills,
            nice_to_have_skills=parsed_jd.nice_to_have_skills,
            user_skills_str=user_skills_str,
            entry_skills=all_entry_skills,
            matched_skills=skill_bridge.matched,
            adjacent_skills=skill_bridge.adjacent,
        )

        # ── Enrich entries with DB data ────────────────────────────────
        from app.models.work_entry import WorkEntry
        self._enrich_from_db(experience_entries, oss_entries, project_entries)

        # ── Assemble Resume JSON ───────────────────────────────────────
        resume_data = {
            "name": profile.name,
            "contact": {
                "email": profile.email,
                "phone": profile.phone or "",
                "github": profile.github or "",
                "linkedin": profile.linkedin or "",
                "location": profile.location or "",
            },
            "email": profile.email,
            "phone": profile.phone or "",
            "github": profile.github or "",
            "linkedin": profile.linkedin or "",
            "location": profile.location or "",
            "education": [
                {
                    "institution": profile.college or "",
                    "degree": profile.degree or "",
                    "year": profile.graduation_year or "",
                    "coursework": profile.coursework or "",
                }
            ] if (profile.college or profile.degree) else [],
            "experience": experience_entries,
            "open_source": oss_entries,
            "projects": project_entries,
            "skills": skills_section,
            "interests": "",
        }

        # Clean internal fields
        for exp in resume_data["experience"]:
            exp.pop("_work_entry_id", None)
        for oss in resume_data["open_source"]:
            oss.pop("_work_entry_id", None)

        # ── Stage 5: ATS Verification ──────────────────────────────────
        resume_text = build_resume_text(resume_data)
        ats_result = calculate_ats_score(resume_text, parsed_jd.ats_keywords)
        resume_data["ats_score"] = ats_result["score"]
        resume_data["ats_matched"] = ats_result["matched"]
        resume_data["ats_missing"] = ats_result["missing_high_priority"]
        resume_data["ats_notes"] = (
            f"{ats_result['score']}% keyword match. "
            f"Matched: {len(ats_result['matched'])}/{len(parsed_jd.ats_keywords)} keywords. "
            f"Missing: {', '.join(ats_result['missing_high_priority'][:3]) or 'none'}"
        )

        logger.info(f"Stage 5 complete: ATS score = {ats_result['score']}%")

        # If ATS score is low, try to inject missing keywords into skills
        if ats_result["score"] < 70 and ats_result["missing_high_priority"]:
            self._inject_missing_keywords(resume_data, ats_result["missing_high_priority"])

        # ── Stage 6: Render PDF & Page-Fit ─────────────────────────────
        latex_content = None
        pdf_path = None
        try:
            from app.services.pdf_service import render_resume_to_latex, get_pdf_page_count
            
            # First pass
            latex_content = render_resume_to_latex(resume_data, profile=profile)
            pdf_path = render_pdf(latex_content)
            
            # If > 1 page, run a shrink pass
            if pdf_path and get_pdf_page_count(pdf_path) > 1:
                logger.info("PDF exceeded 1 page, running shrink pass...")
                
                # Shrink 1: Reduce bullets per entry to max 3 (if not already)
                for exp in resume_data["experience"]:
                    if len(exp.get("bullets", [])) > 3:
                        exp["bullets"] = exp["bullets"][:3]
                
                # Shrink 2: Reduce OSS and Projects
                if len(resume_data["projects"]) > 2:
                    resume_data["projects"] = resume_data["projects"][:2]
                
                if len(resume_data["open_source"]) > 1:
                    resume_data["open_source"] = resume_data["open_source"][:1]
                
                # Re-compile
                latex_content = render_resume_to_latex(resume_data, profile=profile)
                pdf_path = render_pdf(latex_content)
                
                # If STILL > 1 page, aggressive shrink
                if pdf_path and get_pdf_page_count(pdf_path) > 1:
                    logger.info("PDF still > 1 page, running aggressive shrink...")
                    for exp in resume_data["experience"]:
                        if len(exp.get("bullets", [])) > 2:
                            exp["bullets"] = exp["bullets"][:2]
                    
                    if len(resume_data["projects"]) > 1:
                        resume_data["projects"] = resume_data["projects"][:1]
                        
                    latex_content = render_resume_to_latex(resume_data, profile=profile)
                    pdf_path = render_pdf(latex_content)

        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")

        # ── Save Records ──────────────────────────────────────────────
        from app.models.resume_history import ResumeHistory

        resume = GeneratedResume(
            id=resume_id,
            job_description=job_description,
            generated_content=json.dumps(resume_data, indent=2),
            generated_latex=latex_content,
            pdf_path=pdf_path,
            score=float(ats_result["score"]),
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
        logger.info(f"Generated resume {resume_id} (ATS score: {ats_result['score']}%)")
        return resume

    def _enrich_from_db(self, experiences: list, oss_entries: list, projects: list):
        """Enrich generated entries with actual DB data (dates, URLs, etc.)."""
        from app.models.work_entry import WorkEntry

        # Collect all work_entry_ids
        all_ids = set()
        for entries in [experiences, oss_entries]:
            for entry in entries:
                eid = entry.get("_work_entry_id")
                if eid:
                    all_ids.add(eid)

        if not all_ids:
            return

        # Fetch from DB
        db_entries = self.db.query(WorkEntry).filter(WorkEntry.id.in_(all_ids)).all()
        db_map = {e.id: e for e in db_entries}

        # Enrich experiences
        for exp in experiences:
            eid = exp.get("_work_entry_id")
            db_entry = db_map.get(eid)
            if db_entry:
                exp["date_range"] = db_entry.date_range or ""
                if db_entry.role:
                    exp["title"] = db_entry.role
                if db_entry.company:
                    exp["company"] = db_entry.company

        # Enrich OSS
        for oss in oss_entries:
            eid = oss.get("_work_entry_id")
            db_entry = db_map.get(eid)
            if db_entry:
                oss["duration"] = db_entry.date_range or ""
                if db_entry.github_url:
                    # Extract org GitHub URL
                    oss["org_github"] = db_entry.github_url.replace("https://", "")

        # Enrich projects with github_url from retrieval metadata
        # (projects don't have _work_entry_id currently, but we can match by title)

    def _inject_missing_keywords(self, resume_data: dict, missing_keywords: list[str]):
        """Attempt to inject missing ATS keywords into the skills section.

        Only adds keywords that are plausibly related to existing skills.
        """
        skills = resume_data.get("skills", {})
        if not isinstance(skills, dict):
            return

        # Try to categorize and add missing keywords
        for kw in missing_keywords[:3]:
            kw_lower = kw.lower()

            # Check if it's already in any skills category
            already_present = False
            for cat_skills in skills.values():
                if isinstance(cat_skills, list) and any(kw_lower == s.lower() for s in cat_skills):
                    already_present = True
                    break

            if already_present:
                continue

            # Simple heuristic categorization
            if any(lang in kw_lower for lang in ["python", "java", "go", "rust", "typescript", "javascript", "c++", "ruby", "swift", "kotlin"]):
                skills.setdefault("languages", []).append(kw)
            elif any(fw in kw_lower for fw in ["react", "vue", "angular", "django", "flask", "fastapi", "spring", "express", "next", "node"]):
                skills.setdefault("backend", []).append(kw)
            elif any(db in kw_lower for db in ["postgres", "mysql", "mongo", "redis", "elastic", "dynamo", "sqlite", "cassandra"]):
                skills.setdefault("databases", []).append(kw)
            elif any(infra in kw_lower for infra in ["docker", "kubernetes", "aws", "gcp", "azure", "terraform", "jenkins", "ci/cd", "github actions"]):
                skills.setdefault("infra", []).append(kw)
            else:
                # Default to tools or concepts
                skills.setdefault("tools", []).append(kw)

        resume_data["skills"] = skills
