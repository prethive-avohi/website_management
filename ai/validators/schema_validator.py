import json
import frappe


def validate_content_json(content: dict, template_schema: dict) -> list[str]:
    """
    Validate content dict against the template's JSON Schema.
    Returns a list of validation error messages (empty = valid).
    Gracefully degrades if jsonschema is not installed.
    """
    if not template_schema:
        return []

    try:
        import jsonschema
    except ImportError:
        frappe.log_error(
            title="PDCMS: jsonschema not installed",
            message="Install jsonschema: bench pip install jsonschema",
        )
        return []

    validator = jsonschema.Draft7Validator(template_schema)
    return [e.message for e in sorted(validator.iter_errors(content), key=str)]


def parse_llm_response(raw: str) -> dict:
    """
    Parse raw LLM text into a Python dict.
    Strips markdown fences, extracts the outermost JSON object.
    Raises frappe.ValidationError on parse failure.
    """
    text = raw.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        frappe.throw(
            f"AI response is not valid JSON: {e}\n\nRaw (first 1000 chars):\n{raw[:1000]}"
        )


def ensure_canonical_structure(data: dict) -> dict:
    """
    Ensure the top-level content dict always has the canonical keys.
    Missing keys default to empty values, extra keys are preserved.
    """
    canonical = {
        "hero": {},
        "sections": [],
        "seo": {},
        "faq": [],
        "cta": {},
    }
    canonical.update(data)
    return canonical
