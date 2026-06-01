"""
Renders a CMS template file with content_json injected.

Template files use {{dot.path}} placeholders:
  {{hero.headline}}        → content["hero"]["headline"]
  {{features.0.title}}     → content["features"][0]["title"]
  {{seo.meta_description}} → content["seo"]["meta_description"]
"""
import json
import os
import re

import frappe


def render_preview(doctype: str, doc_name: str) -> str:
    """
    Load the doc's template file and inject content_json.
    Returns rendered HTML string.
    """
    doc = frappe.get_doc(doctype, doc_name)

    if not doc.template:
        frappe.throw("No template selected on this document.")

    template_doc = frappe.get_doc("CMS Template", doc.template)

    if not template_doc.template_file:
        frappe.throw(
            f"Template '{doc.template}' has no template file uploaded. "
            "Upload an HTML or Astro file in CMS Template → Template File."
        )

    template_html = _read_template_file(template_doc.template_file)

    content = {}
    if doc.content_json:
        try:
            content = json.loads(doc.content_json)
        except json.JSONDecodeError:
            frappe.throw("content_json on this document is not valid JSON.")

    rendered = _inject(template_html, content)
    return rendered


def _read_template_file(file_url: str) -> str:
    """Resolve Frappe file URL to disk path and read contents."""
    site_path = frappe.utils.get_site_path()

    # file_url is like /files/my-template.html or /private/files/my-template.html
    if file_url.startswith("/private/files/"):
        rel = file_url.lstrip("/")
    elif file_url.startswith("/files/"):
        rel = "public/" + file_url.lstrip("/")
    else:
        rel = "public/files/" + os.path.basename(file_url)

    full_path = os.path.join(site_path, rel)

    if not os.path.exists(full_path):
        frappe.throw(f"Template file not found on disk: {file_url}")

    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def _inject(template: str, content: dict) -> str:
    """Replace all {{dot.path}} placeholders with values from content dict."""

    def replacer(match):
        path = match.group(1).strip()
        value = _resolve_path(content, path)
        if value is None:
            return match.group(0)  # leave placeholder if not found
        return str(value)

    return re.sub(r"\{\{([\w.]+)\}\}", replacer, template)


def _resolve_path(data, path: str):
    """
    Traverse nested dict/list using dot-notation path.
    e.g. "features.0.title" → data["features"][0]["title"]
    """
    parts = path.split(".")
    current = data
    for part in parts:
        if current is None:
            return None
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
