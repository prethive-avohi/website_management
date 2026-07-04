"""
GET /api/method/paideia_cms.api.v1.courses.get_course?slug=<slug>&lang=<lang>
GET /api/method/paideia_cms.api.v1.courses.get_courses
"""
import json
import frappe
from paideia_cms.api.response import success, not_found
from paideia_cms.cms.services.cache_service import get_cached, set_cached
from paideia_cms.cms.services.image_utils import apply_image_overrides


@frappe.whitelist(allow_guest=True)
def get_course(slug: str, lang: str = "en") -> dict:
    slug = slug.strip("/")
    cache_key = f"pdcms:course:{slug}:{lang}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    course = frappe.db.get_value(
        "CMS Course",
        {"slug": slug, "workflow_state": "Published"},
        ["name", "title", "slug", "template", "content_json", "image_overrides",
         "meta_title", "meta_description", "og_image", "canonical_url",
         "duration", "study_level", "institution", "instructor", "featured_image"],
        as_dict=True,
    )
    if not course:
        return not_found(f"Course '{slug}'")

    content = _resolve_content(course, lang)
    content = apply_image_overrides(content, course.image_overrides or "")

    data = {
        "title": course.title,
        "slug": course.slug,
        "template": course.template,
        "astro_component": frappe.db.get_value("CMS Template", course.template, "astro_component") or "",
        "institution": course.institution or "",
        "study_level": course.study_level or "",
        "duration": course.duration or "",
        "instructor": course.instructor or "",
        "featured_image": course.featured_image or "",
        "content": content,
        "seo": {
            "meta_title": course.meta_title or course.title,
            "meta_description": course.meta_description or "",
            "og_image": course.og_image or course.featured_image or "",
            "canonical_url": course.canonical_url or "",
        },
    }

    response = success(data, meta={"lang": lang, "slug": slug})
    set_cached(cache_key, response)
    return response


@frappe.whitelist(allow_guest=True)
def get_courses(lang: str = "en", limit: int = 20, offset: int = 0) -> dict:
    courses = frappe.get_all(
        "CMS Course",
        filters={"workflow_state": "Published"},
        fields=["title", "slug", "template", "institution", "study_level",
                "duration", "instructor", "featured_image", "meta_description"],
        order_by="modified desc",
        limit=int(limit),
        start=int(offset),
    )
    total = frappe.db.count("CMS Course", {"workflow_state": "Published"})
    return success(courses, meta={"total": total, "limit": int(limit), "offset": int(offset)})


def _resolve_content(course, lang: str) -> dict:
    if lang != "en":
        trans = frappe.db.get_value(
            "CMS Translation",
            {
                "reference_doctype": "CMS Course",
                "reference_name": course.name,
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
    if course.content_json:
        try:
            return json.loads(course.content_json)
        except json.JSONDecodeError:
            pass
    return {}
