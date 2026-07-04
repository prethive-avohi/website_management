import json
import frappe
from frappe.model.document import Document
from paideia_cms.utils.slugify import slugify
from paideia_cms.cms.services.deploy_trigger import trigger_deploy
from paideia_cms.cms.services.cache_service import invalidate_course, invalidate_registry


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
        if not self.is_new():
            self._maybe_create_slug_redirect()

    def after_insert(self):
        if self.source_file:
            frappe.enqueue(
                "paideia_cms.jobs.ai_generation.run_course_generation",
                queue="long",
                timeout=600,
                course_name=self.name,
            )

    def on_trash(self):
        if self.ai_job:
            frappe.db.set_value("CMS Course", self.name, "ai_job", None)
            frappe.db.delete("AI Job Log", {"name": self.ai_job})
        frappe.db.delete("AI Job Log", {
            "reference_doctype": "CMS Course",
            "reference_name": self.name,
        })

    def on_update(self):
        invalidate_course(self.slug)
        invalidate_registry()
        if self.workflow_state == "Published" and self.has_value_changed("workflow_state"):
            trigger_deploy(f"CMS Course '{self.slug}' published")

    def _maybe_create_slug_redirect(self):
        old_slug = frappe.db.get_value("CMS Course", self.name, "slug")
        if not old_slug or old_slug == self.slug:
            return
        old_state = frappe.db.get_value("CMS Course", self.name, "workflow_state")
        if old_state != "Published":
            return
        if frappe.db.exists("CMS Redirect", {"old_slug": old_slug, "active": 1}):
            return
        frappe.get_doc({
            "doctype": "CMS Redirect",
            "old_slug": old_slug,
            "new_slug": self.slug,
            "redirect_type": "301",
            "active": 1,
            "content_type": "CMS Course",
            "source_name": self.name,
            "created_on": frappe.utils.now(),
        }).insert(ignore_permissions=True)

    def _ensure_unique_slug(self):
        existing = frappe.db.exists("CMS Course", {"slug": self.slug})
        if existing and existing != self.name:
            self.slug = f"{self.slug}-{frappe.generate_hash(length=4)}"
