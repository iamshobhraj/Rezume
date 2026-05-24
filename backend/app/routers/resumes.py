"""Resume generation and retrieval endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.generated_resume import GeneratedResume
from app.providers.manager import ProviderManager
from app.schemas.resume import ResumeGenerateRequest, ResumeListResponse, ResumeResponse
from app.services.generation import ResumeGenerationService

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/generate", response_model=ResumeResponse)
def generate_resume(body: ResumeGenerateRequest, db: Session = Depends(get_db)):
    """Generate a tailored resume for the given job description."""
    pm = ProviderManager(db)
    service = ResumeGenerationService(db, pm)

    try:
        resume = service.generate_resume(body.job_description)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume generation failed: {str(e)}")

    return ResumeResponse(
        id=resume.id,
        job_description=resume.job_description,
        generated_content=resume.generated_content,
        generated_latex=resume.generated_latex,
        pdf_path=resume.pdf_path,
        score=resume.score,
        created_at=resume.created_at,
    )


@router.get("", response_model=list[ResumeListResponse])
def list_resumes(db: Session = Depends(get_db)):
    """List all previously generated resumes."""
    resumes = db.query(GeneratedResume).order_by(GeneratedResume.created_at.desc()).all()
    return [
        ResumeListResponse(
            id=r.id,
            job_description_preview=r.job_description[:200],
            score=r.score,
            has_pdf=bool(r.pdf_path),
            created_at=r.created_at,
        )
        for r in resumes
    ]


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    """Get a specific generated resume by ID."""
    resume = db.query(GeneratedResume).get(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return ResumeResponse(
        id=resume.id,
        job_description=resume.job_description,
        generated_content=resume.generated_content,
        generated_latex=resume.generated_latex,
        pdf_path=resume.pdf_path,
        score=resume.score,
        created_at=resume.created_at,
    )


@router.get("/{resume_id}/pdf")
def download_resume_pdf(resume_id: str, db: Session = Depends(get_db)):
    """Download the generated PDF for a resume."""
    resume = db.query(GeneratedResume).get(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not resume.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available for this resume")

    pdf_path = Path(resume.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"resume_{resume_id[:8]}.pdf",
    )
