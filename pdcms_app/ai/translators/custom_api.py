import json
import requests
import frappe
from .base import BaseTranslator


class CustomAPITranslator(BaseTranslator):
    """
    Generic pluggable translator that POSTs content JSON to an external API.

    Expected request body:
      { "content": {...}, "source_lang": "en", "target_lang": "ar" }

    Expected response body:
      { "translated": {...} }
    """

    def __init__(self, api_url: str, api_key: str | None = None):
        self.api_url = api_url
        self.api_key = api_key

    def translate(self, content: dict, source_lang: str, target_lang: str) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.post(
            self.api_url,
            headers=headers,
            json={"content": content, "source_lang": source_lang, "target_lang": target_lang},
            timeout=120,
        )

        if response.status_code != 200:
            frappe.throw(
                f"Translation API error ({response.status_code}): {response.text[:500]}"
            )

        result = response.json()
        translated = result.get("translated")
        if not isinstance(translated, dict):
            frappe.throw("Translation API returned unexpected format (expected 'translated' key).")
        return translated
