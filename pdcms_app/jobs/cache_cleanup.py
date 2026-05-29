import frappe


def evict_expired():
    frappe.cache().delete_keys("pdcms:*:expired")
