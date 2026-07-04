"""
API response cache — Redis primary layer.

Key patterns:
  pdcms:page:{slug}:{lang}
  pdcms:blog:{slug}:{lang}
  pdcms:course:{slug}:{lang}
  pdcms:registry:published_pages
  pdcms:registry:template_registry

Invalidation:
  - Per-doc: delete_keys("pdcms:{type}:{slug}:*") on on_update
  - Full registry: delete_keys("pdcms:registry:*") on any publish
  - All cache: delete_keys("pdcms:*") via Frappe Desk "Clear Cache"
"""
import json
import frappe

_DEFAULT_TTL = 300  # 5 minutes fallback if CMS Settings not yet configured


def get_cached(cache_key: str) -> dict | None:
    raw = frappe.cache().get_value(cache_key)
    if raw is None:
        return None
    try:
        return json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    except (json.JSONDecodeError, TypeError):
        return None


def set_cached(cache_key: str, data: dict, ttl: int | None = None):
    if ttl is None:
        ttl = _get_ttl()
    serialized = json.dumps(data, ensure_ascii=False, default=str)
    frappe.cache().set_value(cache_key, serialized, expires_in_sec=ttl)


def invalidate(pattern: str):
    """Delete all cache keys matching the given pattern (Redis KEYS glob)."""
    frappe.cache().delete_keys(pattern)


def invalidate_page(slug: str):
    frappe.cache().delete_keys(f"pdcms:page:{slug}:*")


def invalidate_blog(slug: str):
    frappe.cache().delete_keys(f"pdcms:blog:{slug}:*")


def invalidate_course(slug: str):
    frappe.cache().delete_keys(f"pdcms:course:{slug}:*")


def invalidate_registry():
    """Called on any publish/unpublish — registry list is now stale."""
    frappe.cache().delete_keys("pdcms:registry:*")


def invalidate_all():
    frappe.cache().delete_keys("pdcms:*")


def _get_ttl() -> int:
    try:
        settings = frappe.get_cached_doc("CMS Settings")
        return int(settings.api_cache_ttl or _DEFAULT_TTL)
    except Exception:
        return _DEFAULT_TTL
