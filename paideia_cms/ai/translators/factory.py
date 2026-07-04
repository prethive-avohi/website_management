import frappe
from .base import BaseTranslator


def get_translator() -> BaseTranslator | None:
    """
    Return a configured translator from CMS Settings.
    Returns None if translation provider is set to 'None'.
    """
    settings = frappe.get_single("CMS Settings")
    provider = settings.translation_provider

    if not provider or provider == "None":
        return None

    api_key = settings.get_password("translation_api_key", raise_exception=False) or ""
    api_url = settings.translation_api_url or ""

    if provider == "DeepL":
        if not api_key:
            frappe.throw("DeepL API key is not configured in CMS Settings → Translation.")
        from .deepl import DeepLTranslator
        return DeepLTranslator(api_key=api_key, api_url=api_url)

    if provider == "Google Translate":
        if not api_key:
            frappe.throw("Google Translate API key is not configured in CMS Settings → Translation.")
        from .google_translate import GoogleTranslateTranslator
        return GoogleTranslateTranslator(api_key=api_key)

    if provider == "Custom API":
        from .custom_api import CustomAPITranslator
        return CustomAPITranslator(api_url=api_url, api_key=api_key or None)

    frappe.throw(f"Unsupported translation provider: {provider}")
