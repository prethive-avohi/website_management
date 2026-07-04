"""
Merges editor-uploaded image URLs into AI-generated content_json.
Keeps AI output and image management separate:
  - AI fills text fields via content_json
  - Editors upload images → stored in image_overrides
  - API merges both before returning to the frontend
"""
import json
import copy


def apply_image_overrides(content: dict, overrides_json: str) -> dict:
    """
    Applies image_overrides onto content using dot-path notation.

    overrides_json: '{"hero.image": "/files/hero.jpg", "seo.og_image": "/files/og.jpg"}'
    Returns a new dict with image URLs set at the correct paths.
    """
    if not overrides_json:
        return content
    try:
        overrides = json.loads(overrides_json)
    except (json.JSONDecodeError, TypeError):
        return content

    if not overrides or not isinstance(overrides, dict):
        return content

    result = copy.deepcopy(content)
    for dot_path, url in overrides.items():
        if url and dot_path:
            _set_nested(result, dot_path.split("."), url)
    return result


def _set_nested(d: dict, keys: list, value):
    for key in keys[:-1]:
        if key not in d or not isinstance(d[key], dict):
            d[key] = {}
        d = d[key]
    d[keys[-1]] = value
