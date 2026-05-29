"""
Workflow action handlers for CMS content state transitions.
Registered as server-side workflow actions in Frappe Workflow.
"""
import frappe


def publish(doc, method=None):
    """Called when workflow transitions to Published."""
    doc.db_set("published_at", frappe.utils.now())
    doc.db_set("published_by", frappe.session.user)
    from pdcms_app.cms.services.cache_service import invalidate
    invalidate(f"pdcms:*:{doc.slug}:*")


def archive(doc, method=None):
    """Called when workflow transitions to Archived."""
    from pdcms_app.cms.services.cache_service import invalidate
    invalidate(f"pdcms:*:{doc.slug}:*")
