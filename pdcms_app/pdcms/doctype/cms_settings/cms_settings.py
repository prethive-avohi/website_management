import frappe
from frappe.model.document import Document


class CMSSettings(Document):
    def validate(self):
        if self.api_cache_ttl and self.api_cache_ttl < 0:
            frappe.throw("Cache TTL must be a positive integer.")
