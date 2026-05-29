import frappe


def purge_old_logs():
    """Delete AI Job Log records older than 90 days."""
    cutoff = frappe.utils.add_days(frappe.utils.today(), -90)
    old = frappe.get_all(
        "AI Job Log",
        filters={"creation": ["<", cutoff]},
        fields=["name"],
        limit=1000,
    )
    for row in old:
        frappe.delete_doc("AI Job Log", row.name, ignore_permissions=True)
    if old:
        frappe.db.commit()
