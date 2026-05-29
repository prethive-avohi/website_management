import frappe


def log_info(title: str, message: str):
    frappe.logger("pdcms").info(f"[{title}] {message}")


def log_error(title: str, message: str | None = None):
    frappe.log_error(
        title=f"PDCMS: {title}",
        message=message or frappe.get_traceback(with_context=True),
    )
