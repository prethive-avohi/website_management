import io
import json
import traceback

import frappe
import requests

# ---------------------------------------------------------------------------
# Hardcoded fallback schemas used when CMS Template has no json_schema set
# ---------------------------------------------------------------------------

LANDING_PAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "hero": {
            "type": "object",
            "properties": {
                "headline":    {"type": "string"},
                "subheadline": {"type": "string"},
                "cta_text":    {"type": "string"},
                "cta_url":     {"type": "string"}
            }
        },
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title":       {"type": "string"},
                    "description": {"type": "string"},
                    "icon":        {"type": "string"}
                }
            }
        },
        "about": {
            "type": "object",
            "properties": {
                "heading": {"type": "string"},
                "body":    {"type": "string"}
            }
        },
        "cta_section": {
            "type": "object",
            "properties": {
                "heading":      {"type": "string"},
                "button_label": {"type": "string"},
                "button_url":   {"type": "string"}
            }
        },
        "seo": {
            "type": "object",
            "properties": {
                "meta_title":       {"type": "string"},
                "meta_description": {"type": "string"}
            }
        }
    }
}

BLOG_SCHEMA = {
    "type": "object",
    "properties": {
        "intro":    {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "body":    {"type": "string"}
                }
            }
        },
        "conclusion": {"type": "string"},
        "tags":       {"type": "array", "items": {"type": "string"}},
        "seo": {
            "type": "object",
            "properties": {
                "meta_title":       {"type": "string"},
                "meta_description": {"type": "string"}
            }
        }
    }
}

COURSE_SCHEMA = {
    "type": "object",
    "properties": {
        "overview":   {"type": "string"},
        "objectives": {"type": "array", "items": {"type": "string"}},
        "modules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title":   {"type": "string"},
                    "summary": {"type": "string"},
                    "lessons": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "seo": {
            "type": "object",
            "properties": {
                "meta_title":       {"type": "string"},
                "meta_description": {"type": "string"}
            }
        }
    }
}

# ---------------------------------------------------------------------------
# Hardcoded prompts used when CMS Prompt records are not configured
# ---------------------------------------------------------------------------

LANDING_PAGE_PROMPT = """You are a professional web content strategist.

Read the following document content and generate a complete landing page JSON structure.

Document:
{content}

Output JSON that matches this schema exactly:
{schema}

Rules:
- hero.headline: punchy, max 10 words
- hero.subheadline: one sentence value proposition
- hero.cta_text: action verb phrase e.g. "Get Started Free"
- features: extract 3-5 key features/benefits from the document
- about.body: 2-3 sentences about the company/product
- cta_section: a closing call to action
- seo.meta_title: max 60 characters
- seo.meta_description: max 160 characters
- Return ONLY valid JSON, no explanation, no markdown fences.
"""

BLOG_PROMPT = """You are a professional blog writer and editor.

Read the following document content and generate a structured blog post JSON.

Document:
{content}

Output JSON that matches this schema exactly:
{schema}

Rules:
- intro: 2-3 sentence hook that draws the reader in
- sections: break the content into 3-6 logical sections, each with a heading and body paragraph
- conclusion: 2-3 sentence wrap-up with a takeaway
- tags: 3-5 relevant topic tags (lowercase, single words or short phrases)
- seo.meta_title: max 60 characters, include main keyword
- seo.meta_description: max 160 characters, summarise the post
- Return ONLY valid JSON, no explanation, no markdown fences.
"""

COURSE_PROMPT = """You are an instructional designer and curriculum expert.

Read the following document content and generate a structured course JSON.

Document:
{content}

Output JSON that matches this schema exactly:
{schema}

Rules:
- overview: 3-4 sentence description of what the course covers
- objectives: 4-6 bullet-style learning outcomes starting with action verbs
- modules: break content into 3-8 logical modules, each with a title, summary, and list of lesson titles
- seo.meta_title: max 60 characters
- seo.meta_description: max 160 characters
- Return ONLY valid JSON, no explanation, no markdown fences.
"""


# ---------------------------------------------------------------------------
# Public entry points — called by frappe.enqueue
# ---------------------------------------------------------------------------

def run_page_generation(page_name):
    _run_generation("CMS Page", page_name, "Landing Page")


def run_blog_generation(blog_name):
    _run_generation("CMS Blog", blog_name, "Blog")


def run_course_generation(course_name):
    _run_generation("CMS Course", course_name, "Course")


# ---------------------------------------------------------------------------
# Core generation pipeline
# ---------------------------------------------------------------------------

def _run_generation(doctype, doc_name, content_type):
    doc = frappe.get_doc(doctype, doc_name)

    # Create AI Job Log
    job_log = frappe.get_doc({
        "doctype": "AI Job Log",
        "reference_doctype": doctype,
        "reference_name": doc_name,
        "job_type": "Generate",
        "status": "Queued",
    })
    job_log.insert(ignore_permissions=True)
    frappe.db.commit()

    doc.db_set("ai_job", job_log.name)
    doc.db_set("generation_status", "Queued")

    try:
        job_log.mark_running()
        doc.db_set("generation_status", "Extracting")

        raw_text = _extract_text(doc.source_file)
        if not raw_text or not raw_text.strip():
            frappe.throw("Could not extract text from the uploaded file.")

        doc.db_set("generation_status", "Generating")

        schema, prompt_text = _get_schema_and_prompt(doc, content_type)
        filled_prompt = prompt_text.replace("{content}", raw_text[:8000]).replace(
            "{schema}", json.dumps(schema, indent=2)
        )

        raw_response = _call_ai(filled_prompt)
        content_json = _parse_json_response(raw_response)

        doc.db_set("content_json", json.dumps(content_json, indent=2))
        doc.db_set("generation_status", "Completed")
        job_log.mark_completed(raw_response)
        frappe.db.commit()

    except Exception:
        err = traceback.format_exc()
        doc.db_set("generation_status", "Failed")
        doc.db_set("ai_error_log", err[:10000])
        job_log.mark_failed(err)
        frappe.db.commit()
        raise


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_text(file_url):
    if not file_url:
        return ""

    file_path = frappe.get_site_path("public", file_url.lstrip("/files/"))
    if not file_path:
        return ""

    import os
    full_path = os.path.join(frappe.utils.get_site_path(), "public", file_url.lstrip("/"))

    if not os.path.exists(full_path):
        frappe.throw(f"Source file not found on disk: {file_url}")

    if file_url.lower().endswith(".pdf"):
        return _extract_pdf(full_path)
    elif file_url.lower().endswith(".docx"):
        return _extract_docx(full_path)
    else:
        frappe.throw("Unsupported file type. Please upload a PDF or DOCX file.")


def _extract_pdf(path):
    try:
        import PyPDF2
        text = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text() or "")
        return "\n".join(text)
    except Exception as e:
        frappe.throw(f"PDF extraction failed: {e}")


def _extract_docx(path):
    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        frappe.throw(f"DOCX extraction failed: {e}")


# ---------------------------------------------------------------------------
# Schema + prompt resolution
# ---------------------------------------------------------------------------

def _get_schema_and_prompt(doc, content_type):
    # Try to load schema from linked CMS Template
    schema = {}
    prompt_text = ""

    if doc.template:
        template = frappe.get_doc("CMS Template", doc.template)
        schema = template.get_schema()

        prompts = template.get_prompts()
        if prompts:
            # Use the first active prompt's text
            prompt_doc = frappe.get_doc("CMS Prompt", prompts[0]["name"])
            prompt_text = prompt_doc.prompt_text

    # Fall back to hardcoded defaults if nothing configured
    if not schema:
        schema = _default_schema(content_type)
    if not prompt_text:
        prompt_text = _default_prompt(content_type)

    return schema, prompt_text


def _default_schema(content_type):
    mapping = {
        "Landing Page": LANDING_PAGE_SCHEMA,
        "Blog":         BLOG_SCHEMA,
        "Course":       COURSE_SCHEMA,
    }
    return mapping.get(content_type, LANDING_PAGE_SCHEMA)


def _default_prompt(content_type):
    mapping = {
        "Landing Page": LANDING_PAGE_PROMPT,
        "Blog":         BLOG_PROMPT,
        "Course":       COURSE_PROMPT,
    }
    return mapping.get(content_type, LANDING_PAGE_PROMPT)


# ---------------------------------------------------------------------------
# AI provider dispatch
# ---------------------------------------------------------------------------

def _call_ai(prompt):
    settings = frappe.get_single("CMS Settings")
    provider = settings.ai_provider

    if provider == "Groq":
        return _call_groq(prompt, settings)
    elif provider == "OpenAI":
        return _call_openai(prompt, settings)
    elif provider == "Claude":
        return _call_claude(prompt, settings)
    elif provider == "Ollama":
        return _call_ollama(prompt, settings)
    else:
        frappe.throw(f"Unsupported AI provider: {provider}. Configure CMS Settings.")


def _call_groq(prompt, settings):
    api_key = settings.get_password("groq_api_key")
    if not api_key:
        frappe.throw("Groq API key not set in CMS Settings.")

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": settings.groq_model or "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 8192,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_openai(prompt, settings):
    api_key = settings.get_password("openai_api_key")
    if not api_key:
        frappe.throw("OpenAI API key not set in CMS Settings.")

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": settings.openai_model or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 8192,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_claude(prompt, settings):
    api_key = settings.get_password("claude_api_key")
    if not api_key:
        frappe.throw("Claude API key not set in CMS Settings.")

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.claude_model or "claude-sonnet-4-6",
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def _call_ollama(prompt, settings):
    base_url = settings.ollama_url or "http://localhost:11434"
    resp = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": settings.ollama_model or "mistral",
            "prompt": prompt,
            "stream": False,
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["response"]


# ---------------------------------------------------------------------------
# JSON parsing — strips markdown fences if AI wraps response
# ---------------------------------------------------------------------------

def _parse_json_response(raw):
    text = raw.strip()

    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        frappe.throw(f"AI returned invalid JSON: {e}\n\nRaw response:\n{raw[:2000]}")
