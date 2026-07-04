"""
GET /api/method/paideia_cms.api.v1.pages.get_page?slug=<slug>&lang=<lang>
GET /api/method/paideia_cms.api.v1.pages.get_slugs
"""
import json
import frappe
from paideia_cms.api.response import success, not_found
from paideia_cms.cms.services.cache_service import get_cached, set_cached
from paideia_cms.cms.services.image_utils import apply_image_overrides


@frappe.whitelist(allow_guest=True)
def get_page(slug: str, lang: str = "en") -> dict:
    slug = slug.strip("/")
    cache_key = f"pdcms:page:{slug}:{lang}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    page = frappe.db.get_value(
        "CMS Page",
        {"slug": slug, "workflow_state": "Published"},
        ["name", "title", "slug", "template", "content_json", "image_overrides",
         "meta_title", "meta_description", "og_title", "og_description",
         "og_image", "canonical_url", "published_at"],
        as_dict=True,
    )
    if not page:
        return not_found(f"Page '{slug}'")

    content = _resolve_content(page, lang)
    content = apply_image_overrides(content, page.image_overrides or "")
    seo = _build_seo(page, content)

    data = {
        "title": page.title,
        "slug": page.slug,
        "template": page.template,
        "astro_component": frappe.db.get_value("CMS Template", page.template, "astro_component") or "",
        "content": content,
        "seo": seo,
        "published_at": str(page.published_at or ""),
    }

    response = success(data, meta={"lang": lang, "slug": slug})
    set_cached(cache_key, response)
    return response


@frappe.whitelist(allow_guest=True)
def get_slugs() -> dict:
    pages = frappe.get_all(
        "CMS Page",
        filters={"workflow_state": "Published"},
        fields=["slug", "title", "template"],
    )
    return success(pages, meta={"count": len(pages)})


def _resolve_content(page, lang: str) -> dict:
    if lang != "en":
        trans = frappe.db.get_value(
            "CMS Translation",
            {
                "reference_doctype": "CMS Page",
                "reference_name": page.name,
                "language": lang,
                "workflow_state": "Published",
            },
            "translated_json",
        )
        if trans:
            try:
                return json.loads(trans)
            except json.JSONDecodeError:
                pass
    if page.content_json:
        try:
            return json.loads(page.content_json)
        except json.JSONDecodeError:
            pass
    return {}


def _build_seo(page, content: dict) -> dict:
    generated_seo = content.get("seo", {})
    return {
        "meta_title": page.meta_title or generated_seo.get("meta_title", page.title),
        "meta_description": page.meta_description or generated_seo.get("meta_description", ""),
        "og_title": page.og_title or generated_seo.get("og_title", page.title),
        "og_description": page.og_description or generated_seo.get("og_description", ""),
        "og_image": page.og_image or "",
        "canonical_url": page.canonical_url or "",
    }
