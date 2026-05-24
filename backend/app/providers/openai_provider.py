"""OpenAI-compatible provider implementation.

Works with OpenAI, Ollama, vLLM, and any OpenAI-compatible API
by simply configuring the base_url.
"""

import logging
from typing import Optional

from openai import OpenAI

from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """Provider using the OpenAI Python SDK.

    Supports any OpenAI-compatible API by configuring base_url:
      - OpenAI: base_url=None (uses default)
      - Ollama: base_url="http://localhost:11434/v1"
      - vLLM:   base_url="http://localhost:8000/v1"
    """

    def __init__(
        self,
        api_key: str,
        chat_model: str,
        embedding_model: str,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.chat_model_name = chat_model
        self.embedding_model_name = embedding_model

    def generate(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text using the OpenAI chat completions API."""
        response = self.client.chat.completions.create(
            model=self.chat_model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def embed(self, text: str) -> list[float]:
        """Generate embeddings using the OpenAI embeddings API."""
        response = self.client.embeddings.create(
            model=self.embedding_model_name,
            input=text,
        )
        return response.data[0].embedding

    def test_connection(self) -> dict:
        """Test connectivity by listing available models."""
        try:
            models = self.client.models.list()
            model_ids = [m.id for m in list(models)[:3]]
            return {
                "ok": True,
                "message": f"Connected. Available models include: {', '.join(model_ids)}",
            }
        except Exception as e:
            return {"ok": False, "message": f"Connection failed: {str(e)}"}
