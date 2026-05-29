import json
import frappe
from frappe.model.document import Document


class CMSTemplate(Document):
    def validate(self):
        self._validate_json_schema()
        self._validate_seo_mapping()

    def _validate_json_schema(self):
        if not self.json_schema:
            return
        try:
            json.loads(self.json_schema)
        except json.JSONDecodeError as e:
            frappe.throw(f"Invalid JSON Schema: {e}")

    def _validate_seo_mapping(self):
        if not self.seo_mapping:
            return
        try:
            json.loads(self.seo_mapping)
        except json.JSONDecodeError as e:
            frappe.throw(f"Invalid SEO Mapping JSON: {e}")

    def get_schema(self) -> dict:
        if not self.json_schema:
            return {}
        return json.loads(self.json_schema)

    def get_prompts(self) -> list:
        return frappe.get_all(
            "CMS Prompt",
            filters={"template": self.name, "is_active": 1},
            fields=["name", "prompt_key", "prompt_text", "section_type", "sort_order"],
            order_by="sort_order asc",
        )
