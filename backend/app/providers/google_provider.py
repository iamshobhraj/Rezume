"""Google GenAI provider implementation."""

import logging

from google import genai
from google.genai import types

from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GoogleProvider(BaseLLMProvider):
    """Provider using Google AI Studio (google-genai SDK).

    Supports both chat generation (Gemini models) and embeddings.
    """

    def __init__(self, api_key: str, chat_model: str, embedding_model: str, **kwargs):
        self.client = genai.Client(api_key=api_key)
        self.chat_model_name = chat_model
        self.embedding_model_name = embedding_model
        self.embedding_dim = kwargs.get("embedding_dim")

    def generate(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text using a Gemini model."""
        # Convert messages to Google's format
        # Google GenAI expects a flat content list or a structured content list.
        # We'll concatenate system + user messages for simplicity
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System instructions: {content}\n\n")
            elif role == "assistant":
                parts.append(f"Previous assistant response: {content}\n\n")
            else:
                parts.append(content)

        prompt = "".join(parts)
        response = self.client.models.generate_content(
            model=self.chat_model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )
        return response.text

    def embed(self, text: str) -> list[float]:
        """Generate embeddings using Google's embedding model."""
        config_kwargs = {"task_type": "retrieval_document"}
        if self.embedding_dim:
            config_kwargs["output_dimensionality"] = self.embedding_dim

        result = self.client.models.embed_content(
            model=self.embedding_model_name,
            contents=text,
            config=types.EmbedContentConfig(**config_kwargs)
        )
        return result.embeddings[0].values

    def test_connection(self) -> dict:
        """Test connectivity by listing available models."""
        try:
            models = list(self.client.models.list())
            model_names = [m.name for m in models[:3]]
            return {
                "ok": True,
                "message": f"Connected. Available models include: {', '.join(model_names)}",
            }
        except Exception as e:
            return {"ok": False, "message": f"Connection failed: {str(e)}"}
