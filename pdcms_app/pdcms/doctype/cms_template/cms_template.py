import json
import frappe
from frappe.model.document import Document

DEFAULT_PROMPT = """Analyze the uploaded document and generate structured content JSON.

Document text:
{content}

You must output JSON that exactly matches this schema:
{schema}

Rules:
- Return ONLY valid JSON. No explanation, no markdown, no code fences.
- Every field in the schema must be present in your output.
- Keep text concise and professional.
- For SEO fields: meta_title max 60 characters, meta_description max 160 characters.
- Do not generate HTML, CSS, or Astro code — only JSON content values."""


class CMSTemplate(Document):
    def before_insert(self):
        if not self.ai_prompt:
            self.ai_prompt = DEFAULT_PROMPT

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

    def get_prompt(self) -> str:
        """Return the template's configured prompt, or the default."""
        if self.ai_prompt and self.ai_prompt.strip():
            return self.ai_prompt
        return DEFAULT_PROMPT

    def get_prompts(self) -> list:
        """Return linked CMS Prompt records (advanced use)."""
        return frappe.get_all(
            "CMS Prompt",
            filters={"template": self.name, "is_active": 1},
            fields=["name", "prompt_key", "prompt_text", "section_type", "sort_order"],
            order_by="sort_order asc",
        )

    def publish(self):
        self.status = "Active"
        self.save()
