"""GitHub integration endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.services.github_service import github_service

router = APIRouter(prefix="/github", tags=["github"])

class FetchRequest(BaseModel):
    username: str

@router.post("/fetch-oss")
async def fetch_oss_prs(request: FetchRequest, db: Session = Depends(get_db)):
    """Fetch merged PRs for a GitHub user and ingest them as OSS Projects."""
    result = await github_service.fetch_oss_contributions(db, request.username)
    return result
