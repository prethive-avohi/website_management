"""
GET /api/method/paideia_cms.api.v1.registry.get_published_pages
GET /api/method/paideia_cms.api.v1.registry.get_template_registry

get_published_pages  — every published page/blog/course in one list for Astro getStaticPaths()
get_template_registry — valid astro_component values + their schema contract
"""
import json
import os
import frappe
from paideia_cms.api.response import success
from paideia_cms.cms.services.cache_service import get_cached, set_cached


@frappe.whitelist(allow_guest=True)
def get_published_pages() -> dict:
    cache_key = "pdcms:registry:published_pages"
    cached = get_cached(cache_key)
    if cached:
        return cached

    pages = _get_pages()
    blogs = _get_blogs()
    courses = _get_courses()

    lang_map = _build_language_map()

    all_entries = []

    for p in pages:
        all_entries.append({
            "slug": p.slug.strip("/"),
            "title": p.title,
            "content_type": "CMS Page",
            "template": p.template,
            "astro_component": frappe.db.get_value("CMS Template", p.template, "astro_component") or "",
            "updated_at": str(p.modified or ""),
            "available_languages": lang_map.get(("CMS Page", p.name), ["en"]),
        })

    for b in blogs:
        all_entries.append({
            "slug": b.slug.strip("/"),
            "title": b.title,
            "content_type": "CMS Blog",
            "template": b.template,
            "astro_component": frappe.db.get_value("CMS Template", b.template, "astro_component") or "",
            "updated_at": str(b.modified or ""),
            "available_languages": lang_map.get(("CMS Blog", b.name), ["en"]),
        })

    for c in courses:
        study_level = (c.study_level or "").lower().replace(" ", "-")
        institution = (c.institution or "").lower()
        all_entries.append({
            "slug": c.slug.strip("/"),
            "title": c.title,
            "content_type": "CMS Course",
            "template": c.template,
            "astro_component": frappe.db.get_value("CMS Template", c.template, "astro_component") or "",
            "institution": institution,
            "study_level": study_level,
            "updated_at": str(c.modified or ""),
            "available_languages": lang_map.get(("CMS Course", c.name), ["en"]),
        })

    response = success(all_entries, meta={"total": len(all_entries)})
    set_cached(cache_key, response)
    return response


def _get_pages():
    return frappe.get_all(
        "CMS Page",
        filters={"workflow_state": "Published"},
        fields=["name", "title", "slug", "template", "modified"],
        order_by="modified desc",
    )


def _get_blogs():
    return frappe.get_all(
        "CMS Blog",
        filters={"workflow_state": "Published"},
        fields=["name", "title", "slug", "template", "modified"],
        order_by="modified desc",
    )


def _get_courses():
    return frappe.get_all(
        "CMS Course",
        filters={"workflow_state": "Published"},
        fields=["name", "title", "slug", "template", "institution", "study_level", "modified"],
        order_by="modified desc",
    )


@frappe.whitelist(allow_guest=True)
def get_template_registry() -> dict:
    """
    Returns the TEMPLATE_REGISTRY.json contract — valid astro_component values,
    their required image slots, and expected schema keys.
    Used by frontend devs and cms_template.js form validation.
    """
    registry_path = os.path.join(
        frappe.get_app_path("paideia_cms"),
        "..", "..", "TEMPLATE_REGISTRY.json"
    )
    try:
        with open(os.path.abspath(registry_path), "r", encoding="utf-8") as f:
            data = json.load(f)
        return success(data.get("components", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return success([])


def _build_language_map() -> dict:
    """
    Returns dict mapping (doctype, name) → [list of published language codes].
    English ("en") is always included as the base language.
    """
    translations = frappe.get_all(
        "CMS Translation",
        filters={"workflow_state": "Published"},
        fields=["reference_doctype", "reference_name", "language"],
    )

    lang_map: dict[tuple, list] = {}
    for t in translations:
        key = (t.reference_doctype, t.reference_name)
        if key not in lang_map:
            lang_map[key] = ["en"]
        if t.language not in lang_map[key]:
            lang_map[key].append(t.language)

    return lang_map
