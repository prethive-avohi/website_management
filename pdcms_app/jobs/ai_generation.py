"""
Background job handlers for AI content generation.
All functions are called via frappe.enqueue() — never synchronously.
"""
import frappe
from pdcms_app.cms.services.document_extractor import extract_text
from pdcms_app.ai.generators.content_generator import generate_content_for_template
from pdcms_app.cms.services.translation_service import enqueue_translation


def _create_job_log(reference_doctype: str, reference_name: str, template: str) -> str:
    """Create and return an AI Job Log record."""
    settings = frappe.get_single("CMS Settings")
    job = frappe.get_doc({
        "doctype": "AI Job Log",
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "job_type": "Generate",
        "status": "Queued",
        "ai_provider": settings.ai_provider,
        "template": template,
    })
    job.insert(ignore_permissions=True)
    frappe.db.commit()
    return job.name


def _run_generation(doctype: str, name: str):
    """
    Core generation pipeline shared by page, blog, course handlers.
    """
    doc = frappe.get_doc(doctype, name)
    job_name = _create_job_log(doctype, name, doc.template)

    doc.db_set("generation_status", "Queued")
    doc.db_set("ai_job", job_name)

    job = frappe.get_doc("AI Job Log", job_name)
    job.mark_running()

    try:
        doc.db_set("generation_status", "Extracting")
        extracted = extract_text(doc.source_file)
        doc.db_set("extracted_text", extracted[:50000])

        doc.db_set("generation_status", "Generating")
        content = generate_content_for_template(
            extracted_text=extracted,
            template_name=doc.template,
            job_log_name=job_name,
        )

        import json
        content_str = json.dumps(content, ensure_ascii=False, indent=2)
        doc.db_set("content_json", content_str)
        doc.db_set("generation_status", "Completed")

        # Populate SEO fields if generated
        seo = content.get("seo", {})
        if seo.get("meta_title"):
            doc.db_set("meta_title", seo["meta_title"][:140])
        if seo.get("meta_description"):
            doc.db_set("meta_description", seo["meta_description"][:300])

        job.mark_completed()
        frappe.db.commit()

        enqueue_translation(doctype, name)

    except Exception as e:
        doc.db_set("generation_status", "Failed")
        doc.db_set("ai_error_log", frappe.get_traceback(with_context=True)[:5000])
        job.mark_failed(frappe.get_traceback(with_context=True))
        frappe.db.commit()
        raise


def run_page_generation(page_name: str):
    _run_generation("CMS Page", page_name)


def run_blog_generation(blog_name: str):
    _run_generation("CMS Blog", blog_name)


def run_course_generation(course_name: str):
    _run_generation("CMS Course", course_name)
