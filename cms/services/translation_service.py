"""
Orchestrates queuing translation jobs for all supported languages of a template.
"""
import frappe


def enqueue_translation(doctype: str, name: str):
    """
    Look up the template's supported_languages and enqueue a translation job
    for each non-English language. Called automatically after successful generation.
    """
    try:
        doc = frappe.get_doc(doctype, name)
        template = frappe.get_doc("CMS Template", doc.template)
        languages_raw = template.supported_languages or ""
        languages = [l.strip() for l in languages_raw.split(",") if l.strip() and l.strip() != "en"]
    except Exception:
        return

    for lang in languages:
        frappe.enqueue(
            "pdcms_app.jobs.translation.run_translation",
            queue="long",
            timeout=300,
            doctype=doctype,
            name=name,
            target_language=lang,
        )
