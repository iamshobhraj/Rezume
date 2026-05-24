"""Anthropic provider implementation.

Note: Anthropic does NOT offer an embeddings API. Using this provider for
embeddings will raise NotImplementedError. Users must pair Anthropic chat
with a different embedding provider (Google, OpenAI, etc.).
"""

import logging

import anthropic

from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Provider using the Anthropic Python SDK (Claude models)."""

    def __init__(self, api_key: str, chat_model: str, embedding_model: str = "", **kwargs):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.chat_model_name = chat_model

    def generate(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text using the Anthropic messages API."""
        # Anthropic requires system message separately
        system_message = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message += msg["content"] + "\n"
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})

        # Ensure messages alternate user/assistant; start with user
        if not chat_messages or chat_messages[0]["role"] != "user":
            chat_messages.insert(0, {"role": "user", "content": "Please proceed."})

        kwargs = {
            "model": self.chat_model_name,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_message.strip():
            kwargs["system"] = system_message.strip()

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def embed(self, text: str) -> list[float]:
        """Not supported – Anthropic does not offer embeddings."""
        raise NotImplementedError(
            "Anthropic does not provide an embeddings API. "
            "Please configure a different provider (Google or OpenAI) for embeddings."
        )

    def test_connection(self) -> dict:
        """Test connectivity by sending a minimal message."""
        try:
            response = self.client.messages.create(
                model=self.chat_model_name,
                messages=[{"role": "user", "content": "Say 'hello' in one word."}],
                max_tokens=10,
            )
            return {
                "ok": True,
                "message": f"Connected. Model responded: {response.content[0].text}",
            }
        except Exception as e:
            return {"ok": False, "message": f"Connection failed: {str(e)}"}
