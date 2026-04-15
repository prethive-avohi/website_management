import frappe
import json


@frappe.whitelist(allow_guest=True)
def get_page(slug):
    """Return a single published page by slug with parsed sections."""
    pages = frappe.get_all(
        "Paideia Web Page",
        filters={"slug": slug, "status": "Published"},
        fields=["name"]
    )
    if not pages:
        frappe.throw("Page not found", frappe.DoesNotExistError)

    doc = frappe.get_doc("Paideia Web Page", pages[0].name)
    page_data = {
        "name": doc.name,
        "title": doc.title,
        "slug": doc.slug,
        "page_type": doc.page_type or "Web Page",
        "audience": doc.audience,
        "meta_title": doc.meta_title,
        "meta_description": doc.meta_description,
        "hero_headline": doc.hero_headline,
        "hero_subheadline": doc.hero_subheadline,
        "hero_cta_label": doc.hero_cta_label,
        "hero_cta_url": doc.hero_cta_url,
        "sections": []
    }

    for section in sorted(doc.sections, key=lambda s: s.order or 0):
        items = []
        if section.items_json:
            try:
                items = json.loads(section.items_json)
            except json.JSONDecodeError:
                items = []

        page_data["sections"].append({
            "section_type": section.section_type,
            "heading": section.heading,
            "subheading": section.subheading,
            "body": section.body,
            "cta_label": section.cta_label,
            "cta_url": section.cta_url,
            "order": section.order,
            "background": section.background or "White",
            "items": items
        })

    return page_data


@frappe.whitelist(allow_guest=True)
def get_all_slugs():
    """Return all published page slugs for Astro getStaticPaths."""
    return frappe.get_all(
        "Paideia Web Page",
        filters={"status": "Published"},
        fields=["slug", "audience", "title"]
    )


@frappe.whitelist(allow_guest=True)
def get_pages_by_audience(audience):
    """Return all published pages for a given audience (includes 'All')."""
    return frappe.get_all(
        "Paideia Web Page",
        filters={"status": "Published", "audience": ["in", [audience, "All"]]},
        fields=["name", "title", "slug", "audience", "hero_headline"]
    )


@frappe.whitelist(allow_guest=True)
def get_site_config():
    """Return the Paideia Site Config singleton."""
    doc = frappe.get_single("Paideia Site Config")
    return {
        "site_name": doc.site_name,
        "contact_email": doc.contact_email,
        "contact_phone": doc.contact_phone,
        "address": doc.address,
        "linkedin_url": doc.linkedin_url
    }


@frappe.whitelist(allow_guest=True)
def get_testimonials(audience=None):
    """Return published testimonials, optionally filtered by audience."""
    filters = {"status": "Published"}
    if audience:
        filters["audience"] = ["in", [audience, "All"]]

    return frappe.get_all(
        "Paideia Testimonial",
        filters=filters,
        fields=["quote", "person_name", "role", "organisation", "audience"]
    )
