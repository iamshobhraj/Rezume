"""WorkEntry CRUD endpoints – manage work experience, projects, and OSS contributions.

API prefix remains /projects for backward compatibility with the frontend.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.work_entry import Chunk, WorkEntry, EntryType
from app.providers.manager import ProviderManager
from app.schemas.project import (
    WorkEntryCreate,
    WorkEntryDetailResponse,
    WorkEntryResponse,
    WorkEntryUpdate,
    ChunkResponse,
    RepoDigestRequest,
)
from app.services.ingestion import ingestion_service
from app.services.qdrant_service import qdrant_service
from app.config import settings
from gitingest import ingest_async

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_response(entry: WorkEntry) -> WorkEntryResponse:
    """Convert a WorkEntry ORM model to response schema."""
    return WorkEntryResponse(
        id=entry.id,
        title=entry.title,
        entry_type=entry.entry_type.value if entry.entry_type else "project",
        company=entry.company,
        role=entry.role,
        start_date=entry.start_date,
        end_date=entry.end_date,
        date_range=entry.date_range,  # computed property
        raw_text=entry.raw_text,
        project_type=entry.entry_type.value if entry.entry_type else "project",  # backward compat
        priority=entry.priority,
        github_url=entry.github_url,
        created_at=entry.created_at,
        chunk_count=len(entry.chunks) if entry.chunks else 0,
    )


def _to_detail_response(entry: WorkEntry) -> WorkEntryDetailResponse:
    """Convert a WorkEntry with chunks to a detailed response."""
    return WorkEntryDetailResponse(
        id=entry.id,
        title=entry.title,
        entry_type=entry.entry_type.value if entry.entry_type else "project",
        company=entry.company,
        role=entry.role,
        start_date=entry.start_date,
        end_date=entry.end_date,
        date_range=entry.date_range,
        raw_text=entry.raw_text,
        project_type=entry.entry_type.value if entry.entry_type else "project",
        priority=entry.priority,
        github_url=entry.github_url,
        created_at=entry.created_at,
        chunk_count=len(entry.chunks) if entry.chunks else 0,
        chunks=[
            ChunkResponse(
                id=c.id,
                chunk_text=c.chunk_text,
                metadata_json=c.metadata_json,
                qdrant_point_id=c.qdrant_point_id,
                created_at=c.created_at,
            )
            for c in (entry.chunks or [])
        ],
    )


def _resolve_entry_type(body) -> EntryType:
    """Resolve entry_type from the request body, handling backward compat."""
    if hasattr(body, "entry_type") and body.entry_type is not None:
        return EntryType(body.entry_type.value)
    # Fallback to project_type if provided (old clients)
    if hasattr(body, "project_type") and body.project_type:
        return WorkEntry.entry_type_from_project_type(body.project_type)
    return EntryType.PROJECT


def _run_ingestion(entry_id: str):
    """Background task to ingest a work entry."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        ingestion_service.db = db
        pm = ProviderManager(db)
        ingestion_service.pm = pm
        ingestion_service.ingest_project(entry_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Ingestion failed for entry {entry_id}: {e}")
    finally:
        db.close()


@router.get("", response_model=list[WorkEntryResponse])
def list_entries(db: Session = Depends(get_db)):
    """List all work entries with chunk counts."""
    entries = db.query(WorkEntry).order_by(WorkEntry.created_at.desc()).all()
    return [_to_response(e) for e in entries]


@router.post("", response_model=WorkEntryResponse, status_code=201)
def create_entry(
    body: WorkEntryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new work entry and trigger background ingestion."""
    entry = WorkEntry(
        id=str(uuid.uuid4()),
        title=body.title,
        entry_type=_resolve_entry_type(body),
        company=body.company,
        role=body.role,
        start_date=body.start_date,
        end_date=body.end_date,
        raw_text=body.raw_text,
        priority=body.priority,
        github_url=body.github_url,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Trigger ingestion in the background
    background_tasks.add_task(_run_ingestion, entry.id)

    return _to_response(entry)


@router.get("/{entry_id}", response_model=WorkEntryDetailResponse)
def get_entry(entry_id: str, db: Session = Depends(get_db)):
    """Get a work entry with all its chunks."""
    entry = db.query(WorkEntry).get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Work entry not found")
    return _to_detail_response(entry)


@router.put("/{entry_id}", response_model=WorkEntryResponse)
def update_entry(
    entry_id: str,
    body: WorkEntryUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Update a work entry. Re-triggers ingestion if raw_text changed."""
    entry = db.query(WorkEntry).get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Work entry not found")

    update_data = body.model_dump(exclude_unset=True)
    text_changed = "raw_text" in update_data and update_data["raw_text"] != entry.raw_text

    # Handle entry_type from either new or legacy field
    if "entry_type" in update_data and update_data["entry_type"] is not None:
        update_data["entry_type"] = EntryType(update_data["entry_type"])
    elif "project_type" in update_data and update_data["project_type"]:
        update_data["entry_type"] = WorkEntry.entry_type_from_project_type(update_data["project_type"])

    # Remove backward-compat fields before setting attributes
    update_data.pop("project_type", None)
    update_data.pop("date_range", None)

    for key, value in update_data.items():
        setattr(entry, key, value)

    db.commit()
    db.refresh(entry)

    if text_changed:
        background_tasks.add_task(_run_ingestion, entry.id)

    return _to_response(entry)


@router.delete("/{entry_id}")
def delete_entry(entry_id: str, db: Session = Depends(get_db)):
    """Delete a work entry, its chunks, and associated Qdrant vectors."""
    entry = db.query(WorkEntry).get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Work entry not found")

    # Delete Qdrant points
    point_ids = [c.qdrant_point_id for c in entry.chunks if c.qdrant_point_id]
    if point_ids:
        try:
            qdrant_service.delete_points(point_ids)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to delete Qdrant points: {e}")

    # Cascade deletes chunks via ORM relationship
    db.delete(entry)
    db.commit()
    return {"detail": f"Work entry '{entry.title}' deleted"}


@router.post("/digest-repo")
async def digest_repository(body: RepoDigestRequest):
    """Digest a GitHub repository into prompt-friendly text using Gitingest."""
    url = body.github_url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        if "/" in url and not url.startswith("github.com/"):
            url = f"https://github.com/{url}"
        else:
            raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")

    # Pass the GitHub token if it exists in settings
    token = settings.github_token if settings.github_token else None

    try:
        summary, tree, content = await ingest_async(url, token=token)
        # Format the result nicely: tree structure + file contents
        full_text = f"Repository: {url}\n\nDirectory Structure:\n{tree}\n\nFiles Content:\n{content}"

        # Extract repository name from URL for suggestions
        repo_name = "Repository"
        parts = url.rstrip("/").split("/")
        if len(parts) >= 2:
            repo_name = parts[-1]

        return {
            "success": True,
            "summary": summary,
            "tree": tree,
            "content": content,
            "full_text": full_text,
            "repo_name": repo_name
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Gitingest failed for {url}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to digest repository: {str(e)}"
        )
