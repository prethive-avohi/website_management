import requests
import frappe
from .base import BaseTranslator, extract_strings, rebuild_with_translations, chunk_list

_API_URL = "https://translation.googleapis.com/language/translate/v2"


class GoogleTranslateTranslator(BaseTranslator):
    """
    Translates content_json via Google Cloud Translation API v2 (Basic).
    Requires a Cloud Translation API key set in CMS Settings.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    def translate(self, content: dict, source_lang: str, target_lang: str) -> dict:
        paths, strings = extract_strings(content)
        if not strings:
            return content

        translated = []
        for batch in chunk_list(strings, 128):
            translated.extend(self._call_api(batch, source_lang, target_lang))

        return rebuild_with_translations(content, paths, translated)

    def _call_api(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        resp = requests.post(
            _API_URL,
            params={"key": self.api_key},
            json={
                "q": texts,
                "source": source_lang,
                "target": target_lang,
                "format": "text",
            },
            timeout=30,
        )

        if resp.status_code != 200:
            frappe.throw(f"Google Translate API error ({resp.status_code}): {resp.text[:400]}")

        return [t["translatedText"] for t in resp.json()["data"]["translations"]]
