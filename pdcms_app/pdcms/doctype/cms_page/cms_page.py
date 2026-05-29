import json
import frappe
from frappe.model.document import Document
from pdcms_app.utils.slugify import slugify


class CMSPage(Document):
    def before_insert(self):
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        self._ensure_unique_slug()

    def validate(self):
        self._validate_content_json()

    def on_update(self):
        if self.workflow_state == "Published" and not self.published_at:
            self.db_set("published_at", frappe.utils.now())
            self.db_set("published_by", frappe.session.user)
        self._invalidate_api_cache()

    def after_insert(self):
        if self.source_file:
            self._enqueue_generation()

    def _validate_content_json(self):
        if not self.content_json:
            return
        try:
            json.loads(self.content_json)
        except json.JSONDecodeError as e:
            frappe.throw(f"Content JSON is invalid: {e}")

    def _ensure_unique_slug(self):
        existing = frappe.db.exists("CMS Page", {"slug": self.slug})
        if existing and existing != self.name:
            self.slug = f"{self.slug}-{frappe.generate_hash(length=4)}"

    def _enqueue_generation(self):
        frappe.enqueue(
            "pdcms_app.jobs.ai_generation.run_page_generation",
            queue="long",
            timeout=600,
            page_name=self.name,
        )

    def _invalidate_api_cache(self):
        frappe.cache().delete_keys(f"pdcms:page:{self.slug}:*")
