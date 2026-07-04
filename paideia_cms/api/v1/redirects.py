"""
GET /api/method/paideia_cms.api.v1.redirects.get_redirects

Returns all active CMS Redirects.
Astro/frontend loads this at build time to generate Vercel redirect rules
or handle 404s at the edge.
"""
import frappe
from paideia_cms.api.response import success


@frappe.whitelist(allow_guest=True)
def get_redirects() -> dict:
    redirects = frappe.get_all(
        "CMS Redirect",
        filters={"active": 1},
        fields=["old_slug", "new_slug", "redirect_type", "content_type"],
        order_by="modified desc",
    )
    return success(redirects, meta={"total": len(redirects)})
