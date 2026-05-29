import frappe


def evict_expired():
    """Delete API Cache records that have passed their expiry time."""
    expired = frappe.get_all(
        "API Cache",
        filters={"expires_at": ["<", frappe.utils.now()]},
        fields=["name"],
        limit=500,
    )
    for row in expired:
        frappe.delete_doc("API Cache", row.name, ignore_permissions=True)
    if expired:
        frappe.db.commit()
