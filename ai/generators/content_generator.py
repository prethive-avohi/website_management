import frappe
from pdcms_app.ai.providers.factory import get_provider
from pdcms_app.ai.validators.schema_validator import (
    parse_llm_response,
    validate_content_json,
    ensure_canonical_structure,
)


def generate_content_for_template(
    extracted_text: str,
    template_name: str,
    job_log_name: str | None = None,
) -> dict:
    """
    Run the full template-driven generation pipeline.

    1. Load template + prompts
    2. For each active prompt, call AI and collect the section output
    3. Merge all section outputs into canonical structure
    4. Validate against template schema
    5. Return final content dict

    Args:
        extracted_text: cleaned document text
        template_name: name of CMS Template record
        job_log_name: optional AI Job Log record to update with snapshots

    Returns:
        Canonical content dict: {hero, sections, seo, faq, cta, ...}
    """
    template = frappe.get_doc("CMS Template", template_name)
    prompts = template.get_prompts()

    if not prompts:
        frappe.throw(f"No active prompts configured for template '{template_name}'.")

    provider = get_provider()
    schema = template.get_schema()

    merged: dict = {}

    for p in prompts:
        prompt_doc = frappe.get_doc("CMS Prompt", p["name"])
        rendered_prompt = prompt_doc.render(content=extracted_text, schema=schema)

        try:
            raw = provider.complete(
                prompt=rendered_prompt,
                system=prompt_doc.system_message or None,
                temperature=prompt_doc.temperature or 0.3,
                max_tokens=prompt_doc.max_tokens or 8192,
            )
        except Exception as e:
            frappe.log_error(
                title=f"PDCMS: prompt {p['prompt_key']} failed",
                message=frappe.get_traceback(with_context=True),
            )
            raise

        section_data = parse_llm_response(raw)

        if job_log_name:
            _append_prompt_snapshot(job_log_name, p["prompt_key"], rendered_prompt, raw)

        merged[p["section_type"]] = section_data.get(p["section_type"], section_data)

    final = ensure_canonical_structure(merged)

    errors = validate_content_json(final, schema)
    if errors:
        frappe.log_error(
            title=f"PDCMS: schema validation warnings for '{template_name}'",
            message="\n".join(errors),
        )

    return final


def _append_prompt_snapshot(job_log_name: str, key: str, prompt: str, response: str):
    try:
        job = frappe.get_doc("AI Job Log", job_log_name)
        existing = job.prompt_snapshot or ""
        separator = "\n\n" + "=" * 60 + "\n"
        job.db_set(
            "prompt_snapshot",
            existing + separator + f"[{key}]\n{prompt[:2000]}\n\nRESPONSE:\n{response[:2000]}",
        )
    except Exception:
        pass
