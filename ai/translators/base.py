from abc import ABC, abstractmethod


class BaseTranslator(ABC):
    """Abstract base for all translation providers."""

    @abstractmethod
    def translate(self, content: dict, source_lang: str, target_lang: str) -> dict:
        """
        Translate a content dict from source_lang to target_lang.
        Returns a new dict with the same structure but translated values.
        """
        ...
