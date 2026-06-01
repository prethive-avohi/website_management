"""
Preview endpoints — return rendered HTML for a CMS document.

Usage (open in browser tab or iframe):
  /api/method/pdcms_app.api.v1.preview.render_page?name=PAGE-0001
  /api/method/pdcms_app.api.v1.preview.render_blog?name=BLOG-0001
  /api/method/pdcms_app.api.v1.preview.render_course?name=COURSE-0001

Requires login (any CMS role).
"""
import frappe
from pdcms_app.cms.services.preview_engine import render_preview


@frappe.whitelist()
def render_page(name: str):
    _require_cms_role()
    return _html_response(render_preview("CMS Page", name))


@frappe.whitelist()
def render_blog(name: str):
    _require_cms_role()
    return _html_response(render_preview("CMS Blog", name))


@frappe.whitelist()
def render_course(name: str):
    _require_cms_role()
    return _html_response(render_preview("CMS Course", name))


@frappe.whitelist()
def render_template_test(template_name: str, content_json: str):
    """Test a template with arbitrary sample JSON — used from CMS Template form."""
    _require_cms_role()
    import json
    from pdcms_app.cms.services.preview_engine import _read_template_file, _inject

    template_doc = frappe.get_doc("CMS Template", template_name)
    if not template_doc.template_file:
        frappe.throw("No template file uploaded on this template.")

    html = _read_template_file(template_doc.template_file)
    try:
        content = json.loads(content_json)
    except json.JSONDecodeError as e:
        frappe.throw(f"Invalid JSON: {e}")

    return _inject(html, content)


def _html_response(html: str):
    frappe.response["content_type"] = "text/html; charset=utf-8"
    frappe.response["filename"] = None
    frappe.response["type"] = "html"
    frappe.response["html"] = html
    return html


def _require_cms_role():
    cms_roles = {"CMS Admin", "Content Editor", "CMS Reviewer", "CMS Publisher", "System Manager"}
    if not cms_roles.intersection(set(frappe.get_roles())):
        frappe.throw("Not permitted", frappe.PermissionError)
