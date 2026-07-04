import frappe
from frappe.model.document import Document
from paideia_cms.cms.services.deploy_trigger import trigger_deploy


class CMSTranslation(Document):
    def on_update(self):
        if self.status == "Completed" and not self.translated_at:
            self.db_set("translated_at", frappe.utils.now())

        # Invalidate API cache whenever content or state changes
        frappe.cache().delete_keys(f"pdcms:*:{self.language}:*")

        # Deploy only when an editor explicitly publishes the translation —
        # not on AI completion, because the translation still needs review.
        if self.workflow_state == "Published" and self.has_value_changed("workflow_state"):
            trigger_deploy(f"Translation '{self.reference_name}' → {self.language} published")
