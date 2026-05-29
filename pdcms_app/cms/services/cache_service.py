"""
API response cache.
Uses Frappe's Redis cache as primary layer; falls back to API Cache DocType for persistence.
"""
import json
import frappe


def get_cached(cache_key: str) -> dict | None:
    raw = frappe.cache().get_value(cache_key)
    if raw:
        try:
            return json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def set_cached(cache_key: str, data: dict, ttl: int | None = None):
    if ttl is None:
        settings = frappe.get_cached_doc("CMS Settings")
        ttl = settings.api_cache_ttl or 300

    serialized = json.dumps(data, ensure_ascii=False)
    frappe.cache().set_value(cache_key, serialized, expires_in_sec=ttl)


def invalidate(pattern: str):
    frappe.cache().delete_keys(pattern)
