import json
import frappe
from frappe.model.document import Document
from pdcms_app.utils.slugify import slugify


class CMSCourse(Document):
    def before_insert(self):
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        self._ensure_unique_slug()

    def validate(self):
        if self.content_json:
            try:
                json.loads(self.content_json)
            except json.JSONDecodeError as e:
                frappe.throw(f"Content JSON is invalid: {e}")

    def after_insert(self):
        if self.source_file:
            frappe.enqueue(
                "pdcms_app.jobs.ai_generation.run_course_generation",
                queue="long",
                timeout=600,
                course_name=self.name,
            )

    def on_update(self):
        frappe.cache().delete_keys(f"pdcms:course:{self.slug}:*")

    def _ensure_unique_slug(self):
        existing = frappe.db.exists("CMS Course", {"slug": self.slug})
        if existing and existing != self.name:
            self.slug = f"{self.slug}-{frappe.generate_hash(length=4)}"
