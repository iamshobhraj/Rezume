"""Project CRUD endpoints – manage engineering projects and OSS contributions."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Chunk, Project
from app.providers.manager import ProviderManager
from app.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectUpdate,
    ChunkResponse,
    RepoDigestRequest,
)
from app.services.ingestion import ingestion_service
from app.services.qdrant_service import qdrant_service
from app.config import settings
from gitingest import ingest_async

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_response(project: Project) -> ProjectResponse:
    """Convert a Project ORM model to response schema."""
    return ProjectResponse(
        id=project.id,
        title=project.title,
        company=project.company,
        role=project.role,
        date_range=project.date_range,
        raw_text=project.raw_text,
        project_type=project.project_type,
        priority=project.priority,
        github_url=project.github_url,
        created_at=project.created_at,
        chunk_count=len(project.chunks) if project.chunks else 0,
    )


def _to_detail_response(project: Project) -> ProjectDetailResponse:
    """Convert a Project with chunks to a detailed response."""
    return ProjectDetailResponse(
        id=project.id,
        title=project.title,
        company=project.company,
        role=project.role,
        date_range=project.date_range,
        raw_text=project.raw_text,
        project_type=project.project_type,
        priority=project.priority,
        github_url=project.github_url,
        created_at=project.created_at,
        chunk_count=len(project.chunks) if project.chunks else 0,
        chunks=[
            ChunkResponse(
                id=c.id,
                chunk_text=c.chunk_text,
                metadata_json=c.metadata_json,
                qdrant_point_id=c.qdrant_point_id,
                created_at=c.created_at,
            )
            for c in (project.chunks or [])
        ],
    )


def _run_ingestion(project_id: str):
    """Background task to ingest a project."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # provider manager will just run inside ingestion
        ingestion_service.db = db
        pm = ProviderManager(db)
        ingestion_service.pm = pm
        ingestion_service.ingest_project(project_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Ingestion failed for project {project_id}: {e}")
    finally:
        db.close()


@router.get("", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """List all projects with chunk counts."""
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [_to_response(p) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    body: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new project and trigger background ingestion."""
    project = Project(
        id=str(uuid.uuid4()),
        title=body.title,
        company=body.company,
        role=body.role,
        date_range=body.date_range,
        raw_text=body.raw_text,
        project_type=body.project_type,
        priority=body.priority,
        github_url=body.github_url,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Trigger ingestion in the background
    background_tasks.add_task(_run_ingestion, project.id)

    return _to_response(project)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a project with all its chunks."""
    project = db.query(Project).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_detail_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    body: ProjectUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Update a project. Re-triggers ingestion if raw_text changed."""
    project = db.query(Project).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = body.model_dump(exclude_unset=True)
    text_changed = "raw_text" in update_data and update_data["raw_text"] != project.raw_text

    for key, value in update_data.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    if text_changed:
        background_tasks.add_task(_run_ingestion, project.id)

    return _to_response(project)


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project, its chunks, and associated Qdrant vectors."""
    project = db.query(Project).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete Qdrant points
    point_ids = [c.qdrant_point_id for c in project.chunks if c.qdrant_point_id]
    if point_ids:
        try:
            qdrant_service.delete_points(point_ids)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to delete Qdrant points: {e}")

    # Cascade deletes chunks via ORM relationship
    db.delete(project)
    db.commit()
    return {"detail": f"Project '{project.title}' deleted"}


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

