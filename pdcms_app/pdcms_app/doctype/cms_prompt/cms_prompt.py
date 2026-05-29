import json
import frappe
from frappe.model.document import Document


class CMSPrompt(Document):
    def validate(self):
        self._validate_output_schema()
        if self.temperature is not None and not (0.0 <= self.temperature <= 2.0):
            frappe.throw("Temperature must be between 0.0 and 2.0")

    def _validate_output_schema(self):
        if not self.output_schema:
            return
        try:
            json.loads(self.output_schema)
        except json.JSONDecodeError as e:
            frappe.throw(f"Invalid Output Schema JSON: {e}")

    def render(self, content: str, schema: dict | None = None) -> str:
        text = self.prompt_text.replace("{content}", content)
        if schema is not None:
            text = text.replace("{schema}", json.dumps(schema, indent=2))
        return text
