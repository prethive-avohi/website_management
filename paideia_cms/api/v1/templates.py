"""
Template API — serves active templates for the CMS User template picker.

GET  /api/method/paideia_cms.api.v1.templates.get_active_templates
GET  /api/method/paideia_cms.api.v1.templates.get_template?name=Landing+Page
POST /api/method/paideia_cms.api.v1.templates.publish_template  (Admin only)
"""
import json
import frappe
from paideia_cms.api.response import success, error, not_found


@frappe.whitelist()
def get_active_templates():
    """Return all Active templates for the template picker."""
    templates = frappe.get_all(
        "CMS Template",
        filters={"status": "Active"},
        fields=[
            "name", "template_name", "template_type",
            "description", "preview_image", "astro_component",
            "version",
        ],
        order_by="template_type asc, template_name asc",
    )
    return success(templates, meta={"count": len(templates)})


@frappe.whitelist()
def get_template(name: str):
    """Return full template detail including schema — used when user selects a template."""
    template = frappe.db.get_value(
        "CMS Template",
        {"name": name, "status": "Active"},
        ["name", "template_name", "template_type", "description",
         "preview_image", "astro_component", "json_schema", "version"],
        as_dict=True,
    )
    if not template:
        return not_found(f"Template '{name}'")

    if template.json_schema:
        try:
            template["schema"] = json.loads(template.json_schema)
        except json.JSONDecodeError:
            template["schema"] = {}
    else:
        template["schema"] = {}

    return success(template)


@frappe.whitelist()
def publish_template(name: str):
    """Set template status to Active — Admin only."""
    _require_admin()
    doc = frappe.get_doc("CMS Template", name)
    if not doc.template_file:
        return error("Upload a template file before publishing.")
    if not doc.json_schema:
        return error("Define a JSON schema before publishing.")
    doc.publish()
    return success({"published": True, "name": name})


def _require_admin():
    if "CMS Admin" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
        frappe.throw("Only CMS Admin can publish templates.", frappe.PermissionError)
