"""Resume endpoints – generate, manage, and download resumes."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.generated_resume import GeneratedResume
from app.models.resume_history import ResumeHistory
from app.providers.manager import ProviderManager
from app.services.generation import ResumeGenerationService

router = APIRouter(prefix="/resumes", tags=["resumes"])


class GenerateResumeRequest(BaseModel):
    job_description: str


class RecompileResumeRequest(BaseModel):
    resume_json: dict


@router.post("/generate")
def generate_resume(request: GenerateResumeRequest, db: Session = Depends(get_db)):
    """Generate a resume for a given job description."""
    pm = ProviderManager(db)
    
    # Check if we have active providers
    if not pm.get_active_chat_provider():
        raise HTTPException(
            status_code=400,
            detail="No active chat provider configured. Please configure one in Settings.",
        )
    if not pm.get_active_embedding_provider():
        raise HTTPException(
            status_code=400,
            detail="No active embedding provider configured. Please configure one in Settings.",
        )

    service = ResumeGenerationService(db, pm)
    try:
        resume = service.generate_resume(request.job_description)
        return {
            "id": resume.id,
            "generated_content": resume.generated_content,
            "pdf_path": resume.pdf_path,
            "score": resume.score,
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Resume generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def list_resumes(db: Session = Depends(get_db)):
    """List all generated resumes."""
    resumes = db.query(GeneratedResume).order_by(GeneratedResume.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "job_description_preview": r.job_description[:100] + "..." if len(r.job_description) > 100 else r.job_description,
            "created_at": r.created_at,
            "score": r.score,
            "has_pdf": bool(r.pdf_path),
        }
        for r in resumes
    ]


@router.get("/{resume_id}")
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    """Get a specific generated resume."""
    resume = db.query(GeneratedResume).get(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return {
        "id": resume.id,
        "job_description": resume.job_description,
        "generated_content": resume.generated_content,
        "pdf_path": resume.pdf_path,
        "score": resume.score,
        "created_at": resume.created_at,
    }


@router.get("/{resume_id}/pdf")
def download_pdf(resume_id: str, db: Session = Depends(get_db)):
    """Download the PDF for a generated resume."""
    resume = db.query(GeneratedResume).get(resume_id)
    if not resume or not resume.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    import os
    if not os.path.exists(resume.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file missing from disk")
        
    return FileResponse(
        resume.pdf_path, 
        media_type="application/pdf",
        filename=f"Resume_{resume_id[:8]}.pdf"
    )


@router.post("/{resume_id}/recompile")
def recompile_resume(
    resume_id: str,
    request: RecompileResumeRequest,
    db: Session = Depends(get_db)
):
    """Recompile the PDF from edited JSON data."""
    import uuid
    import logging
    from app.services.pdf_service import render_resume_to_latex, render_pdf
    from app.models.user_profile import UserProfile

    logger = logging.getLogger(__name__)
    
    resume = db.query(GeneratedResume).get(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    profile = db.query(UserProfile).first()
    
    try:
        # Re-render LaTeX
        latex_content = render_resume_to_latex(request.resume_json, profile=profile)
        
        # Re-compile PDF
        pdf_path = render_pdf(latex_content)
        
        if not pdf_path:
            raise HTTPException(status_code=500, detail="LaTeX compilation failed. Check your JSON formatting.")
            
        # Update the main record
        resume.generated_content = json.dumps(request.resume_json, indent=2)
        resume.generated_latex = latex_content
        resume.pdf_path = pdf_path
        
        # Calculate new score if possible
        try:
            from app.services.ats_verifier import build_resume_text, calculate_ats_score
            # We need the original parsed JD to recalculate score accurately.
            # As a shortcut, we extract keywords from the existing notes.
            ats_missing = request.resume_json.get("ats_missing", [])
            ats_matched = request.resume_json.get("ats_matched", [])
            all_keywords = ats_matched + ats_missing
            
            if all_keywords:
                resume_text = build_resume_text(request.resume_json)
                ats_result = calculate_ats_score(resume_text, all_keywords)
                resume.score = ats_result["score"]
                # Update the json with the new score details
                request.resume_json["ats_score"] = ats_result["score"]
                request.resume_json["ats_matched"] = ats_result["matched"]
                request.resume_json["ats_missing"] = ats_result["missing_high_priority"]
                resume.generated_content = json.dumps(request.resume_json, indent=2)
        except Exception as e:
            logger.warning(f"Failed to recalculate ATS score on recompile: {e}")

        # Save to history
        history = ResumeHistory(
            id=str(uuid.uuid4()),
            generated_resume_id=resume_id,
            tags="Manual Edit",
            resume_json=resume.generated_content,
        )
        db.add(history)
        
        db.commit()
        
        return {
            "success": True,
            "pdf_path": pdf_path,
            "score": resume.score
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recompile failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
