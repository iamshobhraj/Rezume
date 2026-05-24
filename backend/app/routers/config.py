"""Resume configuration endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.llm_provider import LLMProvider
from app.models.resume_config import ResumeConfig
from app.schemas.config import ResumeConfigResponse, ResumeConfigUpdate
from app.services.qdrant_service import qdrant_service

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ResumeConfigResponse)
def get_config(db: Session = Depends(get_db)):
    """Get the current resume configuration."""
    config = db.query(ResumeConfig).get("default")
    if config is None:
        return ResumeConfigResponse()

    try:
        data = json.loads(config.config_json)
    except json.JSONDecodeError:
        data = {}

    return ResumeConfigResponse(**data)


@router.put("", response_model=ResumeConfigResponse)
def update_config(body: ResumeConfigUpdate, db: Session = Depends(get_db)):
    """Update the resume configuration.

    Can also change active chat/embedding providers via provider IDs.
    """
    config = db.query(ResumeConfig).get("default")
    if config is None:
        config = ResumeConfig(id="default", config_json="{}")
        db.add(config)

    try:
        current_data = json.loads(config.config_json)
    except json.JSONDecodeError:
        current_data = {}

    update_data = body.model_dump(exclude_unset=True)

    # Validate provider IDs if being changed
    if "active_chat_provider_id" in update_data and update_data["active_chat_provider_id"]:
        provider = db.query(LLMProvider).get(update_data["active_chat_provider_id"])
        if provider is None:
            raise HTTPException(status_code=400, detail="Chat provider ID not found")
        # Also update the is_active flags on the provider table
        db.query(LLMProvider).filter(LLMProvider.is_active_chat.is_(True)).update({"is_active_chat": False})
        provider.is_active_chat = True

    if "active_embedding_provider_id" in update_data and update_data["active_embedding_provider_id"]:
        provider = db.query(LLMProvider).get(update_data["active_embedding_provider_id"])
        if provider is None:
            raise HTTPException(status_code=400, detail="Embedding provider ID not found")
        if provider.provider_type == "anthropic":
            raise HTTPException(status_code=400, detail="Anthropic does not support embeddings")
        db.query(LLMProvider).filter(LLMProvider.is_active_embedding.is_(True)).update({"is_active_embedding": False})
        provider.is_active_embedding = True

    current_data.update(update_data)
    config.config_json = json.dumps(current_data)
    db.commit()

    return ResumeConfigResponse(**current_data)
