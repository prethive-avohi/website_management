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

    if provider == "Custom API":
        from .custom_api import CustomAPITranslator
        return CustomAPITranslator(
            api_url=settings.translation_api_url or "",
            api_key=settings.get_password("translation_api_key") or None,
        )

    frappe.throw(f"Unsupported translation provider: {provider}")
