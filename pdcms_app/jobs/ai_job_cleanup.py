import frappe


def purge_old_logs():
    cutoff = frappe.utils.add_days(frappe.utils.nowdate(), -30)
    old_logs = frappe.get_all(
        "AI Job Log",
        filters={"creation": ["<", cutoff]},
        pluck="name",
    )
    for name in old_logs:
        frappe.delete_doc("AI Job Log", name, ignore_permissions=True)
    if old_logs:
        frappe.db.commit()
