import frappe


def has_permission(doc, ptype, user):
    if frappe.has_role("CMS Admin", user):
        return True
    if ptype in ("read", "write", "submit") and frappe.has_role("Content Editor", user):
        return True
    if ptype == "submit" and frappe.has_role("CMS Publisher", user):
        return True
    return None
