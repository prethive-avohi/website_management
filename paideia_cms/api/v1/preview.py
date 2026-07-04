"""
Preview endpoints — return rendered HTML for a CMS document.

Editor preview (requires login):
  /api/method/paideia_cms.api.v1.preview.render_page?name=PAGE-0001
  /api/method/paideia_cms.api.v1.preview.render_blog?name=BLOG-0001
  /api/method/paideia_cms.api.v1.preview.render_course?name=COURSE-0001

Public render (allow_guest — used by Astro at build time):
  /api/method/paideia_cms.api.v1.preview.render_page_content?slug=sblan&lang=en
  /api/method/paideia_cms.api.v1.preview.render_blog_content?slug=my-post&lang=en
"""
import json
import frappe
from paideia_cms.cms.services.preview_engine import render_preview, render_preview_with_content
from paideia_cms.cms.services.cache_service import get_cached, set_cached
from werkzeug.wrappers import Response


@frappe.whitelist()
def render_page(name: str):
    _require_cms_role()
    return Response(render_preview("CMS Page", name), content_type="text/html; charset=utf-8")


@frappe.whitelist()
def render_blog(name: str):
    _require_cms_role()
    return Response(render_preview("CMS Blog", name), content_type="text/html; charset=utf-8")


@frappe.whitelist()
def render_course(name: str):
    _require_cms_role()
    return Response(render_preview("CMS Course", name), content_type="text/html; charset=utf-8")


@frappe.whitelist()
def render_translation(name: str):
    """Preview a CMS Translation using its translated_json through the source doc's template."""
    import json
    _require_cms_role()
    trans = frappe.get_doc("CMS Translation", name)
    if not trans.translated_json:
        frappe.throw("This translation has no translated content yet.")
    try:
        content = json.loads(trans.translated_json)
    except json.JSONDecodeError:
        frappe.throw("translated_json is not valid JSON.")
    from paideia_cms.cms.services.preview_engine import render_preview_with_content
    html = render_preview_with_content(trans.reference_doctype, trans.reference_name, content)
    return Response(html, content_type="text/html; charset=utf-8")


@frappe.whitelist()
def render_template_test(template_name: str, content_json: str):
    """Test a template with arbitrary sample JSON — called via frappe.call(), returns r.message."""
    _require_cms_role()
    import json
    from paideia_cms.cms.services.preview_engine import _read_template_file, _inject

    template_doc = frappe.get_doc("CMS Template", template_name)
    if not template_doc.template_file:
        frappe.throw("No template file uploaded on this template.")

    html = _read_template_file(template_doc.template_file)
    try:
        content = json.loads(content_json)
    except json.JSONDecodeError as e:
        frappe.throw(f"Invalid JSON: {e}")

    return _inject(html, content)


@frappe.whitelist(allow_guest=True)
def render_page_content(slug: str, lang: str = "en"):
    """
    Guest-accessible rendered HTML for a published CMS Page.
    Used by Astro at build time — returns the Jinja2-rendered template body.
    Response is cached with the same TTL as the JSON API.
    """
    slug = slug.strip("/")
    cache_key = f"pdcms:render:page:{slug}:{lang}"
    cached = get_cached(cache_key)
    if cached:
        return Response(cached, content_type="text/html; charset=utf-8")

    page = frappe.db.get_value(
        "CMS Page",
        {"slug": slug, "workflow_state": "Published"},
        ["name", "content_json"],
        as_dict=True,
    )
    if not page:
        return Response("", status=404, content_type="text/html; charset=utf-8")

    content = _resolve_content_for_render("CMS Page", page.name, page.content_json, lang)
    html = render_preview_with_content("CMS Page", page.name, content)
    set_cached(cache_key, html)
    return Response(html, content_type="text/html; charset=utf-8")


@frappe.whitelist(allow_guest=True)
def render_blog_content(slug: str, lang: str = "en"):
    """Guest-accessible rendered HTML for a published CMS Blog."""
    slug = slug.strip("/")
    cache_key = f"pdcms:render:blog:{slug}:{lang}"
    cached = get_cached(cache_key)
    if cached:
        return Response(cached, content_type="text/html; charset=utf-8")

    blog = frappe.db.get_value(
        "CMS Blog",
        {"slug": slug, "workflow_state": "Published"},
        ["name", "content_json"],
        as_dict=True,
    )
    if not blog:
        return Response("", status=404, content_type="text/html; charset=utf-8")

    content = _resolve_content_for_render("CMS Blog", blog.name, blog.content_json, lang)
    html = render_preview_with_content("CMS Blog", blog.name, content)
    set_cached(cache_key, html)
    return Response(html, content_type="text/html; charset=utf-8")


def _resolve_content_for_render(doctype: str, name: str, content_json: str, lang: str) -> dict:
    if lang != "en":
        trans = frappe.db.get_value(
            "CMS Translation",
            {"reference_doctype": doctype, "reference_name": name, "language": lang, "workflow_state": "Published"},
            "translated_json",
        )
        if trans:
            try:
                return json.loads(trans)
            except json.JSONDecodeError:
                pass
    try:
        return json.loads(content_json or "{}")
    except json.JSONDecodeError:
        return {}


def _require_cms_role():
    cms_roles = {"CMS Admin", "Content Editor", "CMS Reviewer", "CMS Publisher", "System Manager"}
    if not cms_roles.intersection(set(frappe.get_roles())):
        frappe.throw("Not permitted", frappe.PermissionError)
