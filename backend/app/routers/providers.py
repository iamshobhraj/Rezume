"""Provider CRUD endpoints – manage LLM provider configurations."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.llm_provider import LLMProvider
from app.providers.manager import ProviderManager, invalidate_provider_cache
from app.schemas.provider import (
    ProviderActivate,
    ProviderCreate,
    ProviderResponse,
    ProviderTestResponse,
    ProviderUpdate,
)

router = APIRouter(prefix="/providers", tags=["providers"])


def _mask_api_key(key: str) -> str:
    """Mask an API key, showing only the last 4 characters."""
    if len(key) <= 4:
        return "****"
    return "*" * (len(key) - 4) + key[-4:]


def _to_response(provider: LLMProvider) -> ProviderResponse:
    """Convert an ORM model to a response schema with masked key."""
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        api_key_masked=_mask_api_key(provider.api_key),
        chat_model=provider.chat_model,
        embedding_model=provider.embedding_model,
        embedding_dim=provider.embedding_dim,
        is_active_chat=provider.is_active_chat,
        is_active_embedding=provider.is_active_embedding,
        created_at=provider.created_at,
    )


@router.get("", response_model=list[ProviderResponse])
def list_providers(db: Session = Depends(get_db)):
    """List all configured providers (API keys masked)."""
    providers = db.query(LLMProvider).order_by(LLMProvider.created_at).all()
    return [_to_response(p) for p in providers]


@router.post("", response_model=ProviderResponse, status_code=201)
def create_provider(body: ProviderCreate, db: Session = Depends(get_db)):
    """Add a new LLM provider.

    If this is the first provider with chat/embedding capability,
    it's automatically set as active.
    """
    # Check for name uniqueness
    existing = db.query(LLMProvider).filter(LLMProvider.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Provider with name '{body.name}' already exists")

    provider = LLMProvider(
        id=str(uuid.uuid4()),
        name=body.name,
        provider_type=body.provider_type,
        base_url=body.base_url,
        api_key=body.api_key,
        chat_model=body.chat_model,
        embedding_model=body.embedding_model,
        embedding_dim=body.embedding_dim,
    )

    # Auto-activate if no active provider exists for chat/embedding
    active_chat = db.query(LLMProvider).filter(LLMProvider.is_active_chat.is_(True)).first()
    if active_chat is None:
        provider.is_active_chat = True

    active_embedding = db.query(LLMProvider).filter(LLMProvider.is_active_embedding.is_(True)).first()
    if active_embedding is None and body.provider_type != "anthropic":
        provider.is_active_embedding = True

    db.add(provider)
    db.commit()
    db.refresh(provider)
    return _to_response(provider)


@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: str, body: ProviderUpdate, db: Session = Depends(get_db)):
    """Update an existing provider's configuration."""
    provider = db.query(LLMProvider).get(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(provider, key, value)

    db.commit()
    db.refresh(provider)
    invalidate_provider_cache(provider_id)
    return _to_response(provider)


@router.delete("/{provider_id}")
def delete_provider(provider_id: str, db: Session = Depends(get_db)):
    """Delete a provider.

    Blocks deletion if it's the only active chat or embedding provider.
    """
    provider = db.query(LLMProvider).get(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Check if it's the only active provider
    if provider.is_active_chat:
        other_chat = (
            db.query(LLMProvider)
            .filter(LLMProvider.is_active_chat.is_(True), LLMProvider.id != provider_id)
            .first()
        )
        if other_chat is None:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete the only active chat provider. Activate another provider first.",
            )

    if provider.is_active_embedding:
        other_emb = (
            db.query(LLMProvider)
            .filter(LLMProvider.is_active_embedding.is_(True), LLMProvider.id != provider_id)
            .first()
        )
        if other_emb is None:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete the only active embedding provider. Activate another provider first.",
            )

    db.delete(provider)
    db.commit()
    invalidate_provider_cache(provider_id)
    return {"detail": f"Provider '{provider.name}' deleted"}


@router.post("/{provider_id}/test", response_model=ProviderTestResponse)
def test_provider(provider_id: str, db: Session = Depends(get_db)):
    """Test connectivity for a specific provider."""
    provider = db.query(LLMProvider).get(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    manager = ProviderManager(db)
    result = manager.test_provider(provider)
    return ProviderTestResponse(**result)


@router.put("/{provider_id}/activate", response_model=ProviderResponse)
def activate_provider(provider_id: str, body: ProviderActivate, db: Session = Depends(get_db)):
    """Set a provider as the active chat and/or embedding provider.

    Deactivates any previously active provider for the same role.
    """
    provider = db.query(LLMProvider).get(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    if not body.set_active_chat and not body.set_active_embedding:
        raise HTTPException(status_code=400, detail="Must set at least one of set_active_chat or set_active_embedding")

    if body.set_active_chat:
        # Deactivate all other chat providers
        db.query(LLMProvider).filter(LLMProvider.is_active_chat.is_(True)).update({"is_active_chat": False})
        provider.is_active_chat = True

    if body.set_active_embedding:
        if provider.provider_type == "anthropic":
            raise HTTPException(
                status_code=400,
                detail="Anthropic does not support embeddings. Choose a different provider for embeddings.",
            )
        # Deactivate all other embedding providers
        db.query(LLMProvider).filter(LLMProvider.is_active_embedding.is_(True)).update({"is_active_embedding": False})
        provider.is_active_embedding = True

    db.commit()
    db.refresh(provider)
    return _to_response(provider)
