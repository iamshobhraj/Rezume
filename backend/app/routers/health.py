"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Simple health check for container readiness probes."""
    return {"status": "ok"}
