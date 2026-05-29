import json
import frappe
from frappe.model.document import Document
from pdcms_app.utils.slugify import slugify


class CMSBlog(Document):
    def before_insert(self):
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        self._ensure_unique_slug()
        if not self.author:
            self.author = frappe.session.user

    def validate(self):
        if self.content_json:
            try:
                json.loads(self.content_json)
            except json.JSONDecodeError as e:
                frappe.throw(f"Content JSON is invalid: {e}")

    def after_insert(self):
        if self.source_file:
            frappe.enqueue(
                "pdcms_app.jobs.ai_generation.run_blog_generation",
                queue="long",
                timeout=600,
                blog_name=self.name,
            )

    def on_update(self):
        frappe.cache().delete_keys(f"pdcms:blog:{self.slug}:*")

    def _ensure_unique_slug(self):
        existing = frappe.db.exists("CMS Blog", {"slug": self.slug})
        if existing and existing != self.name:
            self.slug = f"{self.slug}-{frappe.generate_hash(length=4)}"
