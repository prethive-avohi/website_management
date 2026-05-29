"""
Background job handler for translation workflow.
Called via frappe.enqueue() — never synchronously.
"""
import json
import frappe
from pdcms_app.ai.translators.factory import get_translator


def run_translation(doctype: str, name: str, target_language: str):
    """
    Translate content_json of a CMS Page/Blog/Course to target_language.
    Stores result in CMS Translation record.
    """
    translator = get_translator()
    if translator is None:
        return  # Translation provider is 'None' — skip silently

    doc = frappe.get_doc(doctype, name)
    if not doc.content_json:
        return

    content = json.loads(doc.content_json)

    trans_name = _get_or_create_translation(doctype, name, target_language)
    trans = frappe.get_doc("CMS Translation", trans_name)
    trans.db_set("status", "Queued")

    job = frappe.get_doc({
        "doctype": "AI Job Log",
        "reference_doctype": "CMS Translation",
        "reference_name": trans_name,
        "job_type": "Translate",
        "status": "Queued",
        "language": target_language,
    })
    job.insert(ignore_permissions=True)
    frappe.db.commit()
    job.mark_running()

    try:
        translated = translator.translate(content, source_lang="en", target_lang=target_language)
        trans.db_set("translated_json", json.dumps(translated, ensure_ascii=False))
        trans.db_set("status", "Completed")
        trans.db_set("provider", frappe.get_single("CMS Settings").translation_provider)
        trans.db_set("translation_job", job.name)
        job.mark_completed()
        frappe.db.commit()
    except Exception:
        trans.db_set("status", "Failed")
        job.mark_failed(frappe.get_traceback(with_context=True))
        frappe.db.commit()
        raise


def _get_or_create_translation(doctype: str, name: str, language: str) -> str:
    existing = frappe.db.get_value(
        "CMS Translation",
        {"reference_doctype": doctype, "reference_name": name, "language": language},
        "name",
    )
    if existing:
        return existing

    trans = frappe.get_doc({
        "doctype": "CMS Translation",
        "reference_doctype": doctype,
        "reference_name": name,
        "language": language,
        "status": "Pending",
    })
    trans.insert(ignore_permissions=True)
    frappe.db.commit()
    return trans.name
