import json
import re
import frappe
from frappe.model.document import Document


def _slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


class PaideiaContentGenerator(Document):

    def before_save(self):
        if not self.slug:
            self.slug = _slugify(self.title)


@frappe.whitelist()
def generate_page(docname):
    """Enqueue background generation job and return immediately."""
    doc = frappe.get_doc("Paideia Content Generator", docname)

    doc.status = "Extracting"
    doc.error_log = ""
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.enqueue(
        "paideia_cms.paideia_cms.doctype.paideia_content_generator.paideia_content_generator._run_generation",
        docname=docname,
        queue="long",
        timeout=600,
        now=False,
    )

    return {"status": "queued", "docname": docname}


def _run_generation(docname):
    """Background worker: extract text -> AI -> store JSON."""
    doc = frappe.get_doc("Paideia Content Generator", docname)

    try:
        from paideia_cms.utils.document_extractor import extract_text_from_file
        extracted = extract_text_from_file(doc.source_file)
        doc.extracted_text = extracted
        doc.status = "Generating"
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        from paideia_cms.utils.content_generator import generate_page_content
        page_data = generate_page_content(extracted, doc.page_type)

        doc.generated_content = json.dumps(page_data, ensure_ascii=False, indent=2)
        doc.status = "Completed"
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Paideia Content Generator: {docname}")
        doc.status = "Failed"
        doc.error_log = str(e)
        doc.save(ignore_permissions=True)
        frappe.db.commit()


@frappe.whitelist()
def reset_status(docname):
    """Reset a stuck Extracting/Generating record back to Pending."""
    doc = frappe.get_doc("Paideia Content Generator", docname)
    doc.status = "Pending"
    doc.error_log = ""
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "reset"}


@frappe.whitelist(allow_guest=True)
def get_content(slug):
    """Return the generated content JSON for a completed generator record by slug."""
    name = frappe.db.get_value("Paideia Content Generator", {"slug": slug}, "name")
    if not name:
        frappe.throw(f"No record found for slug: {slug}", frappe.DoesNotExistError)
    doc = frappe.get_doc("Paideia Content Generator", name)
    if doc.status != "Completed" or not doc.generated_content:
        frappe.throw("Content not yet generated", frappe.DoesNotExistError)

    return {
        "docname": doc.name,
        "title": doc.title,
        "slug": doc.slug,
        "page_type": doc.page_type,
        "audience": doc.audience,
        "extracted_text": doc.extracted_text or "",
        "content": json.loads(doc.generated_content),
    }
