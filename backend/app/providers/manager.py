"""ProviderManager – factory, dispatch, and client caching for LLM providers."""

import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy.orm import Session

from app.models.llm_provider import LLMProvider
from app.providers.base import BaseLLMProvider
from app.providers.google_provider import GoogleProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.anthropic_provider import AnthropicProvider

logger = logging.getLogger(__name__)

# Factory mapping from provider_type to class
PROVIDER_CLASSES: dict[str, type[BaseLLMProvider]] = {
    "google": GoogleProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "custom": OpenAIProvider,  # Custom OpenAI-compatible endpoints
}


def _build_client(provider: LLMProvider) -> BaseLLMProvider:
    """Instantiate a provider client from a database model row."""
    cls = PROVIDER_CLASSES.get(provider.provider_type)
    if cls is None:
        raise ValueError(f"Unknown provider type: {provider.provider_type}")

    return cls(
        api_key=provider.api_key,
        chat_model=provider.chat_model,
        embedding_model=provider.embedding_model,
        base_url=provider.base_url,
        embedding_dim=provider.embedding_dim,
    )


# Module-level cache keyed on (provider_id, provider_type, api_key, base_url)
# so that changing a provider's config invalidates the cache entry.
_client_cache: dict[tuple, BaseLLMProvider] = {}


def _cache_key(provider: LLMProvider) -> tuple:
    return (provider.id, provider.provider_type, provider.api_key, provider.base_url)


def _get_or_create_client(provider: LLMProvider) -> BaseLLMProvider:
    """Get a cached client or create a new one."""
    key = _cache_key(provider)
    if key not in _client_cache:
        _client_cache[key] = _build_client(provider)
    return _client_cache[key]


def invalidate_provider_cache(provider_id: str) -> None:
    """Remove any cached client entries for a given provider ID."""
    keys_to_remove = [k for k in _client_cache if k[0] == provider_id]
    for key in keys_to_remove:
        del _client_cache[key]


class ProviderManager:
    """Manages active LLM providers and dispatches generate/embed calls.

    Instantiated per-request with a database session.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_active_chat_provider(self) -> Optional[LLMProvider]:
        """Fetch the provider row marked as active for chat."""
        return self.db.query(LLMProvider).filter(LLMProvider.is_active_chat.is_(True)).first()

    def get_active_embedding_provider(self) -> Optional[LLMProvider]:
        """Fetch the provider row marked as active for embeddings."""
        return self.db.query(LLMProvider).filter(LLMProvider.is_active_embedding.is_(True)).first()

    def get_chat_client(self) -> BaseLLMProvider:
        """Get the client for the active chat provider."""
        provider = self.get_active_chat_provider()
        if provider is None:
            raise RuntimeError("No active chat provider configured. Add a provider in Settings.")
        return _get_or_create_client(provider)

    def get_fallback_chat_client(self) -> Optional[BaseLLMProvider]:
        """Fetch the Google provider client as a fallback if the main one fails."""
        # Find any Google provider in the DB that has an API key configured
        google_provider = self.db.query(LLMProvider).filter(
            LLMProvider.provider_type == "google",
            LLMProvider.api_key != ""
        ).first()
        if google_provider:
            try:
                return _get_or_create_client(google_provider)
            except Exception as e:
                logger.error(f"Failed to instantiate fallback Google provider: {e}")
        return None

    def get_embedding_client(self) -> BaseLLMProvider:
        """Get the client for the active embedding provider."""
        provider = self.get_active_embedding_provider()
        if provider is None:
            raise RuntimeError("No active embedding provider configured. Add a provider in Settings.")
        return _get_or_create_client(provider)

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate text using the active chat provider with automatic rate limit retries and Google fallback."""
        active_provider = self.get_active_chat_provider()
        
        # Check if the active model is Gemini Flash (our final fallback model)
        is_gemini_flash = active_provider and active_provider.provider_type == "google" and "flash" in active_provider.chat_model.lower()

        try:
            client = self.get_chat_client()
        except Exception as e:
            if not is_gemini_flash:
                logger.warning(f"Failed to get active chat client: {e}. Trying fallback Google Gemini client...")
                fallback_client = self.get_fallback_chat_client()
                if fallback_client:
                    # Force the fallback client to use gemini-2.5-flash
                    fallback_client.chat_model_name = "gemini-2.5-flash"
                    return fallback_client.generate(messages, **kwargs)
            raise e

        import time
        max_retries = 3
        delay = 15
        for attempt in range(max_retries + 1):
            try:
                return client.generate(messages, **kwargs)
            except Exception as e:
                err_msg = str(e)
                if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and attempt < max_retries:
                    logger.warning(f"Rate limit hit during generation. Retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                else:
                    # Fallback to gemini-2.5-flash if not already using a flash model
                    if not is_gemini_flash:
                        logger.warning(f"Generation failed on model '{active_provider.chat_model if active_provider else 'unknown'}' with error: {e}. Falling back to gemini-2.5-flash...")
                        fallback_client = self.get_fallback_chat_client()
                        if fallback_client:
                            original_model = getattr(fallback_client, "chat_model_name", None)
                            try:
                                fallback_client.chat_model_name = "gemini-2.5-flash"
                                return fallback_client.generate(messages, **kwargs)
                            except Exception as fallback_error:
                                logger.error(f"Fallback Gemini 2.5 Flash also failed: {fallback_error}")
                                raise e
                            finally:
                                if original_model:
                                    fallback_client.chat_model_name = original_model
                    raise e

    def embed_text(self, text: str) -> list[float]:
        """Generate embeddings using the active embedding provider with automatic rate limit retries."""
        client = self.get_embedding_client()
        import time
        max_retries = 3
        delay = 15
        for attempt in range(max_retries + 1):
            try:
                return client.embed(text)
            except Exception as e:
                err_msg = str(e)
                if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and attempt < max_retries:
                    logger.warning(f"Rate limit hit during embedding. Retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                else:
                    raise e

    def test_provider(self, provider: LLMProvider) -> dict:
        """Test connectivity for a specific provider (not necessarily the active one)."""
        try:
            client = _build_client(provider)
            return client.test_connection()
        except Exception as e:
            return {"ok": False, "message": f"Failed to create client: {str(e)}"}
