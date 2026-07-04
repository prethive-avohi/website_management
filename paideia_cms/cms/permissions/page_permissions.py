import frappe


def has_permission(doc, ptype, user):
    user_roles = frappe.get_roles(user)
    if "CMS Admin" in user_roles:
        return True
    if ptype in ("read", "write", "submit") and "Content Editor" in user_roles:
        return True
    if ptype == "submit" and "CMS Publisher" in user_roles:
        return True
    return None
