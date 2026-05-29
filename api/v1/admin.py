"""
Admin-only API endpoints for triggering generation and translation.
All require login — not guest-accessible.
"""
import frappe
from pdcms_app.api.response import success, error


@frappe.whitelist()
def trigger_generation(doctype: str, name: str) -> dict:
    """Manually re-trigger AI generation for a CMS document."""
    _require_cms_role()

    doc = frappe.get_doc(doctype, name)
    if not doc.source_file:
        return error("No source file attached.")
    if not doc.template:
        return error("No template selected.")

    job_map = {
        "CMS Page": "pdcms_app.jobs.ai_generation.run_page_generation",
        "CMS Blog": "pdcms_app.jobs.ai_generation.run_blog_generation",
        "CMS Course": "pdcms_app.jobs.ai_generation.run_course_generation",
    }
    handler = job_map.get(doctype)
    if not handler:
        return error(f"Generation not supported for {doctype}.")

    kwarg_map = {
        "CMS Page": "page_name",
        "CMS Blog": "blog_name",
        "CMS Course": "course_name",
    }
    frappe.enqueue(handler, queue="long", timeout=600, **{kwarg_map[doctype]: name})
    doc.db_set("generation_status", "Queued")

    return success({"queued": True, "doctype": doctype, "name": name})


@frappe.whitelist()
def trigger_translation(doctype: str, name: str, language: str) -> dict:
    """Manually trigger translation for a specific language."""
    _require_cms_role()

    frappe.enqueue(
        "pdcms_app.jobs.translation.run_translation",
        queue="long",
        timeout=300,
        doctype=doctype,
        name=name,
        target_language=language,
    )
    return success({"queued": True, "language": language})


@frappe.whitelist()
def get_job_status(job_name: str) -> dict:
    _require_cms_role()
    job = frappe.db.get_value(
        "AI Job Log",
        job_name,
        ["status", "started_at", "completed_at", "duration_seconds", "retry_count"],
        as_dict=True,
    )
    if not job:
        return error("Job not found", 404)
    return success(job)


def _require_cms_role():
    cms_roles = {"CMS Admin", "Content Editor", "CMS Reviewer", "CMS Publisher", "System Manager"}
    user_roles = set(frappe.get_roles())
    if not cms_roles.intersection(user_roles):
        frappe.throw("Not permitted", frappe.PermissionError)
