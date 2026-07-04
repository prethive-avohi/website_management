"""
GET /api/method/paideia_cms.api.v1.blogs.get_blog?slug=<slug>&lang=<lang>
GET /api/method/paideia_cms.api.v1.blogs.get_blogs
"""
import json
import frappe
from paideia_cms.api.response import success, not_found
from paideia_cms.cms.services.cache_service import get_cached, set_cached
from paideia_cms.cms.services.image_utils import apply_image_overrides


@frappe.whitelist(allow_guest=True)
def get_blog(slug: str, lang: str = "en") -> dict:
    slug = slug.strip("/")
    cache_key = f"pdcms:blog:{slug}:{lang}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    blog = frappe.db.get_value(
        "CMS Blog",
        {"slug": slug, "workflow_state": "Published"},
        ["name", "title", "slug", "template", "content_json", "image_overrides",
         "meta_title", "meta_description", "og_image", "canonical_url",
         "author", "published_date", "reading_time_minutes", "featured_image"],
        as_dict=True,
    )
    if not blog:
        return not_found(f"Blog '{slug}'")

    content = _resolve_content(blog, lang)
    content = apply_image_overrides(content, blog.image_overrides or "")

    data = {
        "title": blog.title,
        "slug": blog.slug,
        "template": blog.template,
        "astro_component": frappe.db.get_value("CMS Template", blog.template, "astro_component") or "",
        "author": blog.author,
        "published_date": str(blog.published_date or ""),
        "reading_time_minutes": blog.reading_time_minutes,
        "featured_image": blog.featured_image or "",
        "content": content,
        "seo": {
            "meta_title": blog.meta_title or blog.title,
            "meta_description": blog.meta_description or "",
            "og_image": blog.og_image or blog.featured_image or "",
            "canonical_url": blog.canonical_url or "",
        },
    }

    response = success(data, meta={"lang": lang, "slug": slug})
    set_cached(cache_key, response)
    return response


@frappe.whitelist(allow_guest=True)
def get_blogs(lang: str = "en", limit: int = 20, offset: int = 0) -> dict:
    blogs = frappe.get_all(
        "CMS Blog",
        filters={"workflow_state": "Published"},
        fields=["title", "slug", "template", "author", "published_date",
                "reading_time_minutes", "featured_image", "meta_description"],
        order_by="published_date desc",
        limit=int(limit),
        start=int(offset),
    )
    total = frappe.db.count("CMS Blog", {"workflow_state": "Published"})
    return success(blogs, meta={"total": total, "limit": int(limit), "offset": int(offset)})


def _resolve_content(blog, lang: str) -> dict:
    if lang != "en":
        trans = frappe.db.get_value(
            "CMS Translation",
            {
                "reference_doctype": "CMS Blog",
                "reference_name": blog.name,
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
    if blog.content_json:
        try:
            return json.loads(blog.content_json)
        except json.JSONDecodeError:
            pass
    return {}
