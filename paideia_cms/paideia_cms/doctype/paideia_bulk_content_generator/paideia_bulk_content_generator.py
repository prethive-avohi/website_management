import re
import frappe
from frappe import Document


def _slugify(text):
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


class PaideiaBulkContentGenerator(Document):

    def before_save(self):
        # Auto-fill titles from filenames and generate slugs
        for row in self.files:
            if not row.file_title and row.source_file:
                # Extract filename without extension
                import os
                fname = os.path.basename(row.source_file)
                fname = os.path.splitext(fname)[0]
                # Clean up: replace underscores/hyphens with spaces, title case
                row.file_title = fname.replace("_", " ").replace("-", " ").title()

            if not row.slug and row.file_title:
                row.slug = _slugify(row.file_title)

        self.total_files = len(self.files)


@frappe.whitelist()
def generate_all(docname):
    """Process all pending files in the bulk upload batch."""
    doc = frappe.get_doc("Paideia Bulk Content Generator", docname)

    doc.status = "Processing"
    doc.processed = 0
    doc.failed = 0
    doc.processing_log = ""
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    from paideia_cms.utils.document_extractor import extract_text_from_file
    from paideia_cms.utils.content_generator import generate_page_content

    log_lines = []
    processed_count = 0
    failed_count = 0

    for idx, row in enumerate(doc.files):
        if row.item_status == "Completed":
            processed_count += 1
            log_lines.append(f"**{row.file_title}**: Skipped (already completed)")
            continue

        row.item_status = "Processing"
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        try:
            # Step 1: Extract text
            extracted = extract_text_from_file(row.source_file)

            # Step 2: Determine page type (row override or batch default)
            page_type = row.page_type_override or doc.page_type

            # Step 3: Generate page content via AI
            page_data = generate_page_content(extracted, page_type)

            # Step 4: Create web page
            web_page = _create_web_page_from_row(doc, row, page_data)

            row.generated_page = web_page.name
            row.item_status = "Completed"
            row.error_message = ""
            processed_count += 1
            log_lines.append(
                f"**{row.file_title}**: Created → [{web_page.name}](/app/paideia-web-page/{web_page.name})"
            )

        except Exception as e:
            row.item_status = "Failed"
            row.error_message = str(e)[:500]
            failed_count += 1
            log_lines.append(f"**{row.file_title}**: Failed — {str(e)[:200]}")
            frappe.log_error(
                title=f"Bulk CG: {row.file_title}",
                message=frappe.get_traceback(with_context=True)
            )

        # Update progress after each file
        doc.processed = processed_count
        doc.failed = failed_count
        doc.processing_log = "\n\n".join(log_lines)
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Publish real-time progress to the browser
        frappe.publish_realtime(
            "bulk_content_progress",
            {
                "docname": doc.name,
                "current": idx + 1,
                "total": len(doc.files),
                "file_title": row.file_title,
                "item_status": row.item_status,
            },
            doctype=doc.doctype,
            docname=doc.name,
        )

    # Final status
    if failed_count == 0:
        doc.status = "Completed"
    else:
        doc.status = "Partially Failed"

    doc.processing_log = "\n\n".join(log_lines)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": doc.status,
        "processed": processed_count,
        "failed": failed_count,
    }


def _create_web_page_from_row(doc, row, page_data):
    """Create a Paideia Web Page from a bulk upload row."""
    slug = row.slug or _slugify(row.file_title)

    # Ensure unique slug
    if frappe.db.exists("Paideia Web Page", {"slug": slug}):
        slug = f"{slug}-{frappe.generate_hash(length=4)}"

    web_page = frappe.new_doc("Paideia Web Page")
    web_page.title = row.file_title
    web_page.slug = slug
    web_page.audience = doc.audience or "All"
    web_page.status = "Draft"
    web_page.meta_title = page_data.get("meta_title", row.file_title)
    web_page.meta_description = page_data.get("meta_description", "")
    web_page.hero_headline = page_data.get("hero_headline", row.file_title)
    web_page.hero_subheadline = page_data.get("hero_subheadline", "")
    web_page.hero_cta_label = page_data.get("hero_cta_label", "")
    web_page.hero_cta_url = page_data.get("hero_cta_url", "")

    for i, section in enumerate(page_data.get("sections", [])):
        web_page.append("sections", {
            "section_type": section.get("section_type", "Rich Text"),
            "heading": section.get("heading", ""),
            "subheading": section.get("subheading", ""),
            "body": section.get("body", ""),
            "cta_label": section.get("cta_label", ""),
            "cta_url": section.get("cta_url", ""),
            "order": i + 1,
            "background": section.get("background", "White"),
            "items_json": section.get("items_json", ""),
        })

    web_page.insert(ignore_permissions=True)
    frappe.db.commit()

    return web_page


@frappe.whitelist()
def retry_failed(docname):
    """Retry only the failed items in a batch."""
    doc = frappe.get_doc("Paideia Bulk Content Generator", docname)

    # Reset failed items to Pending
    for row in doc.files:
        if row.item_status == "Failed":
            row.item_status = "Pending"
            row.error_message = ""
            row.generated_page = ""

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Re-run
    return generate_all(docname)
