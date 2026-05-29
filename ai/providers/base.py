from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    """Abstract base for all AI providers. Every provider must implement complete()."""

    DEFAULT_SYSTEM = (
        "You are a web content generator. "
        "Return ONLY valid JSON, no markdown fences, no explanation."
    )

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """Send prompt to the provider and return the raw text response."""
        ...

    def _system(self, override: str | None) -> str:
        return override if override else self.DEFAULT_SYSTEM
