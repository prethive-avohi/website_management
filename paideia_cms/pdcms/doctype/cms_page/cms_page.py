import json
import frappe
from frappe.model.document import Document
from paideia_cms.utils.slugify import slugify
from paideia_cms.cms.services.deploy_trigger import trigger_deploy
from paideia_cms.cms.services.cache_service import invalidate_page, invalidate_registry


class CMSPage(Document):
    def before_insert(self):
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        self._ensure_unique_slug()

    def validate(self):
        self._validate_content_json()
        if not self.is_new():
            self._maybe_create_slug_redirect()

    def on_update(self):
        if self.workflow_state == "Published" and not self.published_at:
            self.db_set("published_at", frappe.utils.now())
            self.db_set("published_by", frappe.session.user)
            trigger_deploy(f"CMS Page '{self.slug}' published")
        self._invalidate_api_cache()

    def after_insert(self):
        if self.source_file:
            self._enqueue_generation()

    def on_trash(self):
        # Frappe v17 order: on_trash → link check → delete.
        # So deleting AI Job Log here clears the link before Frappe's check runs.
        if self.ai_job:
            frappe.db.set_value("CMS Page", self.name, "ai_job", None)
            frappe.db.delete("AI Job Log", {"name": self.ai_job})
        # Also catch any orphaned logs that reference this page via dynamic link
        frappe.db.delete("AI Job Log", {
            "reference_doctype": "CMS Page",
            "reference_name": self.name,
        })

    def _validate_content_json(self):
        if not self.content_json:
            return
        try:
            json.loads(self.content_json)
        except json.JSONDecodeError as e:
            frappe.throw(f"Content JSON is invalid: {e}")

    def _maybe_create_slug_redirect(self):
        old_slug = frappe.db.get_value("CMS Page", self.name, "slug")
        if not old_slug or old_slug == self.slug:
            return
        old_state = frappe.db.get_value("CMS Page", self.name, "workflow_state")
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
            "content_type": "CMS Page",
            "source_name": self.name,
            "created_on": frappe.utils.now(),
        }).insert(ignore_permissions=True)

    def _ensure_unique_slug(self):
        existing = frappe.db.exists("CMS Page", {"slug": self.slug})
        if existing and existing != self.name:
            self.slug = f"{self.slug}-{frappe.generate_hash(length=4)}"

    def _enqueue_generation(self):
        frappe.enqueue(
            "paideia_cms.jobs.ai_generation.run_page_generation",
            queue="long",
            timeout=600,
            page_name=self.name,
        )

    def _invalidate_api_cache(self):
        invalidate_page(self.slug)
        invalidate_registry()
