"""Abstract base class for all LLM providers."""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Interface that all LLM provider implementations must follow.

    Each provider wraps a specific SDK (Google GenAI, OpenAI, Anthropic)
    and exposes a uniform generate/embed/test API.
    """

    @abstractmethod
    def generate(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a text response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles: 'system', 'user', 'assistant'.
            temperature: Sampling temperature (0.0 - 1.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            The generated text content.
        """
        ...

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    def test_connection(self) -> dict:
        """Test connectivity to the provider API.

        Returns:
            A dict with 'ok' (bool) and 'message' (str).
        """
        ...
