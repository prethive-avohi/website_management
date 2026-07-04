import copy
from abc import ABC, abstractmethod


class BaseTranslator(ABC):
    """Abstract base for all translation providers."""

    @abstractmethod
    def translate(self, content: dict, source_lang: str, target_lang: str) -> dict:
        """
        Translate a content dict from source_lang to target_lang.
        Returns a new dict with the same structure but translated string values.
        """
        ...


# ── Shared helpers used by all providers ─────────────────────────────────────

def extract_strings(obj, path=None, paths=None, strings=None):
    """Recursively collect all string leaf values with their key paths."""
    if path is None:
        path = []
    if paths is None:
        paths = []
    if strings is None:
        strings = []

    if isinstance(obj, str):
        if obj.strip():
            paths.append(list(path))
            strings.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            extract_strings(v, path + [k], paths, strings)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            extract_strings(v, path + [i], paths, strings)

    return paths, strings


def rebuild_with_translations(original: dict, paths: list, translated: list) -> dict:
    """Rebuild the content dict substituting translated strings at each path."""
    result = copy.deepcopy(original)
    for path, text in zip(paths, translated):
        node = result
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = text
    return result


def chunk_list(lst: list, size: int):
    """Split a list into chunks of at most `size` items."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]
