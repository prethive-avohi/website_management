import re
import frappe
from frappe.model.document import Document


def _slugify(text):
    """Convert text to a URL-friendly slug."""
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
    """Main workflow: extract text -> send to SLM -> create Paideia Web Page."""
    doc = frappe.get_doc("Paideia Content Generator", docname)

    try:
        doc.status = "Extracting"
        doc.error_log = ""
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Step 1: Extract text from uploaded document
        from paideia_cms.utils.document_extractor import extract_text_from_file
        extracted = extract_text_from_file(doc.source_file)
        doc.extracted_text = extracted

        doc.status = "Generating"
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Step 2: Send to SLM for structured content
        from paideia_cms.utils.content_generator import generate_page_content
        page_data = generate_page_content(extracted, doc.page_type)

        # Step 3: Create Paideia Web Page
        web_page = _create_web_page(doc, page_data)

        doc.generated_page = web_page.name
        doc.status = "Completed"
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "page_name": web_page.name,
            "slug": web_page.slug,
        }

    except Exception as e:
        doc.status = "Failed"
        doc.error_log = str(e)
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.throw(str(e))


def _create_web_page(doc, page_data):
    """Create a Paideia Web Page from the structured content data."""
    slug = doc.slug
    if frappe.db.exists("Paideia Web Page", {"slug": slug}):
        slug = f"{slug}-{frappe.generate_hash(length=4)}"

    web_page = frappe.new_doc("Paideia Web Page")
    web_page.title = doc.title
    web_page.slug = slug
    web_page.page_type = doc.page_type or "Web Page"
    web_page.audience = doc.audience or "All"
    web_page.status = "Draft"
    web_page.meta_title = page_data.get("meta_title", doc.title)
    web_page.meta_description = page_data.get("meta_description", "")
    web_page.hero_headline = page_data.get("hero_headline", doc.title)
    web_page.hero_subheadline = page_data.get("hero_subheadline", "")
    web_page.hero_cta_label = page_data.get("hero_cta_label", "")
    web_page.hero_cta_url = page_data.get("hero_cta_url", "")

    for idx, section in enumerate(page_data.get("sections", [])):
        web_page.append("sections", {
            "section_type": section.get("section_type", "Rich Text"),
            "heading": section.get("heading", ""),
            "subheading": section.get("subheading", ""),
            "body": section.get("body", ""),
            "cta_label": section.get("cta_label", ""),
            "cta_url": section.get("cta_url", ""),
            "order": idx + 1,
            "background": section.get("background", "White"),
            "items_json": section.get("items_json", ""),
        })

    web_page.insert(ignore_permissions=True)
    frappe.db.commit()

    return web_page
