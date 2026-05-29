import frappe
from frappe.model.document import Document


class CMSMedia(Document):
    def before_insert(self):
        self.uploaded_by = frappe.session.user

    def public_url(self) -> str:
        return self.cdn_url or self.file_url or ""
