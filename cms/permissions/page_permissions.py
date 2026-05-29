import frappe

_ADMIN_ROLES = {"CMS Admin", "System Manager"}
_WRITE_ROLES = {"CMS Admin", "Content Editor", "CMS Publisher", "System Manager"}
_READ_ROLES = {"CMS Admin", "Content Editor", "CMS Reviewer", "CMS Publisher", "System Manager"}


def has_permission(doc, ptype="read", user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True

    roles = set(frappe.get_roles(user))

    if ptype in ("read", "select"):
        return bool(roles & _READ_ROLES)
    if ptype in ("write", "create", "submit", "cancel", "amend"):
        return bool(roles & _WRITE_ROLES)
    if ptype == "delete":
        return bool(roles & _ADMIN_ROLES)

    return False
