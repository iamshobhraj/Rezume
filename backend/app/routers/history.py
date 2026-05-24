"""Resume History API endpoints."""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from deepdiff import DeepDiff
from pydantic import BaseModel

from app.database import get_db
from app.models.resume_history import ResumeHistory

router = APIRouter(prefix="/history", tags=["history"])

class ResumeHistoryResponse(BaseModel):
    id: str
    generated_resume_id: str
    tags: str | None
    created_at: str
    
    model_config = {"from_attributes": True}

@router.get("", response_model=list[dict])
def list_history(db: Session = Depends(get_db)):
    """List all past generated resumes."""
    records = db.query(ResumeHistory).order_by(ResumeHistory.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "generated_resume_id": r.generated_resume_id,
            "tags": r.tags,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]

@router.get("/{history_id}")
def get_history(history_id: str, db: Session = Depends(get_db)):
    record = db.query(ResumeHistory).get(history_id)
    if not record:
        raise HTTPException(status_code=404, detail="History not found")
    return {
        "id": record.id,
        "resume_json": json.loads(record.resume_json),
        "tags": record.tags,
    }

@router.get("/diff/{id1}/{id2}")
def compare_history(id1: str, id2: str, db: Session = Depends(get_db)):
    """Compute a JSON diff between two generated resumes."""
    rec1 = db.query(ResumeHistory).get(id1)
    rec2 = db.query(ResumeHistory).get(id2)
    
    if not rec1 or not rec2:
        raise HTTPException(status_code=404, detail="One or both history records not found")
        
    json1 = json.loads(rec1.resume_json)
    json2 = json.loads(rec2.resume_json)
    
    diff = DeepDiff(json1, json2, ignore_order=True)
    return json.loads(diff.to_json())
