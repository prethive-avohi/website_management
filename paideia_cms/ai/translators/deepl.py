import requests
import frappe
from .base import BaseTranslator, extract_strings, rebuild_with_translations, chunk_list

_FREE_URL = "https://api-free.deepl.com/v2/translate"
_PRO_URL = "https://api.deepl.com/v2/translate"


class DeepLTranslator(BaseTranslator):
    """
    Translates content_json via DeepL API v2.
    Uses free tier endpoint by default; set api_url in CMS Settings to switch to pro.
    """

    def __init__(self, api_key: str, api_url: str = ""):
        self.api_key = api_key
        self.endpoint = api_url or _FREE_URL

    def translate(self, content: dict, source_lang: str, target_lang: str) -> dict:
        paths, strings = extract_strings(content)
        if not strings:
            return content

        translated = []
        for batch in chunk_list(strings, 50):
            translated.extend(self._call_api(batch, source_lang, target_lang))

        return rebuild_with_translations(content, paths, translated)

    def _call_api(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        # DeepL uses uppercase language codes; pt-br → PT-BR
        src = source_lang.upper().replace("-", "-")
        tgt = target_lang.upper().replace("-", "-")

        resp = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"DeepL-Auth-Key {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"text": texts, "source_lang": src, "target_lang": tgt},
            timeout=30,
        )

        if resp.status_code != 200:
            frappe.throw(f"DeepL API error ({resp.status_code}): {resp.text[:400]}")

        return [t["text"] for t in resp.json().get("translations", [])]
