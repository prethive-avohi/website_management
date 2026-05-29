import frappe
from frappe.model.document import Document


class CMSTranslation(Document):
    def on_update(self):
        if self.status == "Completed" and not self.translated_at:
            self.db_set("translated_at", frappe.utils.now())
        # Invalidate API cache for this resource + language
        frappe.cache().delete_keys(
            f"pdcms:*:{self.language}:*"
        )
