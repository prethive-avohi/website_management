import json
import frappe
import requests


SECTION_TYPES = [
    "Trust Strip", "Audience Cards", "Feature Cards", "Service Models",
    "Process Steps", "Testimonials", "CTA Banner", "Rich Text",
    "Scholarship List", "FAQ"
]

PROMPT_TEMPLATES = {
    "Landing Page": """You are a web content strategist. Analyze the following document text and create a structured landing page.

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "meta_title": "SEO title (max 60 chars)",
  "meta_description": "SEO description (max 160 chars)",
  "hero_headline": "Main headline for the hero section",
  "hero_subheadline": "Supporting text for the hero section",
  "hero_cta_label": "Call to action button text",
  "hero_cta_url": "#contact",
  "sections": [
    {{
      "section_type": "one of: Rich Text, Feature Cards, Process Steps, CTA Banner, FAQ, Trust Strip",
      "heading": "Section heading",
      "subheading": "Optional subheading",
      "body": "HTML content for Rich Text sections, empty for others",
      "background": "one of: White, Grey, Dark, Accent",
      "cta_label": "Optional CTA text",
      "cta_url": "Optional CTA link",
      "items_json": "JSON array string for card/list sections e.g. [{{\\"title\\":\\"..\\",\\"description\\":\\"..\\"}}, ...]"
    }}
  ]
}}

Create 4-6 sections. For Feature Cards and Process Steps, include items_json with relevant items.
Each item should have "title" and "description" fields.

DOCUMENT TEXT:
{content}""",

    "Blog Post": """You are a content writer. Analyze the following document text and create a structured blog post.

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "meta_title": "SEO title (max 60 chars)",
  "meta_description": "SEO description (max 160 chars)",
  "hero_headline": "Blog post title",
  "hero_subheadline": "Brief summary of the post",
  "hero_cta_label": "",
  "hero_cta_url": "",
  "sections": [
    {{
      "section_type": "Rich Text",
      "heading": "Section heading or empty for intro",
      "subheading": "",
      "body": "<p>Well-formatted HTML content with proper paragraphs, lists, bold, etc.</p>",
      "background": "White",
      "cta_label": "",
      "cta_url": "",
      "items_json": ""
    }}
  ]
}}

Break the content into 3-5 Rich Text sections with clear headings. Use proper HTML formatting.
End with a CTA Banner section if appropriate.

DOCUMENT TEXT:
{content}""",

    "Web Page": """You are a web content designer. Analyze the following document text and create a structured web page.

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "meta_title": "SEO title (max 60 chars)",
  "meta_description": "SEO description (max 160 chars)",
  "hero_headline": "Main page headline",
  "hero_subheadline": "Supporting text",
  "hero_cta_label": "Optional CTA text",
  "hero_cta_url": "#contact",
  "sections": [
    {{
      "section_type": "one of: Rich Text, Feature Cards, Process Steps, CTA Banner, FAQ, Trust Strip",
      "heading": "Section heading",
      "subheading": "Optional subheading",
      "body": "HTML content for Rich Text sections",
      "background": "one of: White, Grey, Dark, Accent",
      "cta_label": "Optional CTA",
      "cta_url": "Optional URL",
      "items_json": "JSON array string for structured sections"
    }}
  ]
}}

Create 3-6 well-structured sections mixing Rich Text with Feature Cards or FAQ as appropriate.
For Feature Cards, items_json should be: [{{"title":"..","description":".."}}, ...]
For FAQ, items_json should be: [{{"question":"..","answer":".."}}, ...]

DOCUMENT TEXT:
{content}"""
}


def get_ai_settings():
    """Load AI provider settings from Paideia CMS Settings singleton."""
    settings = frappe.get_single("Paideia CMS Settings")
    return settings


def generate_page_content(extracted_text, page_type):
    """Route to the correct AI provider based on settings.

    Args:
        extracted_text: The text extracted from the document
        page_type: One of "Landing Page", "Blog Post", "Web Page"

    Returns:
        Parsed JSON dict with page structure
    """
    settings = get_ai_settings()
    provider = settings.ai_provider

    # Truncate very long documents to stay within model context
    max_chars = 8000
    if len(extracted_text) > max_chars:
        extracted_text = extracted_text[:max_chars] + "\n\n[... content truncated for processing ...]"

    prompt = PROMPT_TEMPLATES.get(page_type, PROMPT_TEMPLATES["Web Page"])
    prompt = prompt.format(content=extracted_text)

    if provider == "Ollama (Local)":
        raw = _call_ollama(prompt, settings)
    elif provider == "HuggingFace (Free API)":
        raw = _call_huggingface(prompt, settings)
    elif provider == "Groq (Free API)":
        raw = _call_groq(prompt, settings)
    elif provider == "OpenAI (ChatGPT)":
        raw = _call_openai(prompt, settings)
    elif provider == "Claude (Anthropic)":
        raw = _call_claude(prompt, settings)
    else:
        frappe.throw(f"Unknown AI provider: {provider}")

    return parse_llm_response(raw)


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _call_ollama(prompt, settings):
    """Call local Ollama server."""
    ollama_url = settings.ollama_url or "http://localhost:11434"
    model = settings.ollama_model or "mistral"

    try:
        requests.get(f"{ollama_url}/api/tags", timeout=5).raise_for_status()
    except requests.exceptions.ConnectionError:
        frappe.throw(
            f"Cannot connect to Ollama at {ollama_url}. "
            "Make sure Ollama is running (ollama serve). "
            "On Frappe Cloud, switch to HuggingFace or Groq provider in Paideia CMS Settings."
        )

    response = requests.post(
        f"{ollama_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 4096},
        },
        timeout=300,
    )

    if response.status_code != 200:
        frappe.throw(f"Ollama error ({response.status_code}): {response.text[:500]}")

    return response.json().get("response", "")


def _call_huggingface(prompt, settings):
    """Call HuggingFace Inference API (free tier: ~1000 req/day)."""
    api_token = settings.get_password("hf_api_token")
    if not api_token:
        frappe.throw(
            "HuggingFace API token not set. "
            "Get a free token at huggingface.co/settings/tokens and add it in Paideia CMS Settings."
        )

    model = settings.hf_model or "mistralai/Mistral-7B-Instruct-v0.3"
    api_url = f"https://api-inference.huggingface.co/models/{model}"

    response = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {api_token}"},
        json={
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 4096,
                "temperature": 0.3,
                "return_full_text": False,
            },
        },
        timeout=120,
    )

    if response.status_code == 503:
        # Model is loading
        frappe.throw(
            "The HuggingFace model is loading (cold start). Please try again in 30-60 seconds."
        )

    if response.status_code != 200:
        frappe.throw(f"HuggingFace API error ({response.status_code}): {response.text[:500]}")

    result = response.json()
    if isinstance(result, list) and len(result) > 0:
        return result[0].get("generated_text", "")

    frappe.throw(f"Unexpected HuggingFace response format: {str(result)[:500]}")


def _call_groq(prompt, settings):
    """Call Groq API (free tier: 14,400 req/day, very fast).

    Groq uses an OpenAI-compatible chat completions endpoint.
    """
    api_key = settings.get_password("groq_api_key")
    if not api_key:
        frappe.throw(
            "Groq API key not set. "
            "Get a free key at console.groq.com/keys and add it in Paideia CMS Settings."
        )

    model = settings.groq_model or "llama-3.1-8b-instant"

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a web content generator. Return ONLY valid JSON, no markdown fences, no explanation."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        },
        timeout=120,
    )

    if response.status_code != 200:
        frappe.throw(f"Groq API error ({response.status_code}): {response.text[:500]}")

    result = response.json()
    return result["choices"][0]["message"]["content"]


def _call_openai(prompt, settings):
    """Call OpenAI ChatGPT API.

    Models: gpt-4o-mini (cheap), gpt-4o (best), gpt-4.1-mini, gpt-4.1-nano (cheapest)
    """
    api_key = settings.get_password("openai_api_key")
    if not api_key:
        frappe.throw(
            "OpenAI API key not set. "
            "Get your key at platform.openai.com/api-keys and add it in Paideia CMS Settings."
        )

    model = settings.openai_model or "gpt-4o-mini"

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a web content generator. Return ONLY valid JSON, no markdown fences, no explanation.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        },
        timeout=120,
    )

    if response.status_code == 401:
        frappe.throw("Invalid OpenAI API key. Check your key in Paideia CMS Settings.")

    if response.status_code == 429:
        frappe.throw("OpenAI rate limit exceeded. Please wait a moment and try again.")

    if response.status_code != 200:
        frappe.throw(f"OpenAI API error ({response.status_code}): {response.text[:500]}")

    result = response.json()
    return result["choices"][0]["message"]["content"]


def _call_claude(prompt, settings):
    """Call Anthropic Claude API.

    Models: claude-sonnet-4-6 (balanced), claude-haiku-4-5-20251001 (fast/cheap), claude-opus-4-6 (best)
    """
    api_key = settings.get_password("claude_api_key")
    if not api_key:
        frappe.throw(
            "Anthropic API key not set. "
            "Get your key at console.anthropic.com/settings/keys and add it in Paideia CMS Settings."
        )

    model = settings.claude_model or "claude-sonnet-4-6"

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 4096,
            "system": "You are a web content generator. Return ONLY valid JSON, no markdown fences, no explanation.",
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        },
        timeout=120,
    )

    if response.status_code == 401:
        frappe.throw("Invalid Anthropic API key. Check your key in Paideia CMS Settings.")

    if response.status_code == 429:
        frappe.throw("Anthropic rate limit exceeded. Please wait a moment and try again.")

    if response.status_code != 200:
        frappe.throw(f"Claude API error ({response.status_code}): {response.text[:500]}")

    result = response.json()
    # Claude returns content as a list of content blocks
    content_blocks = result.get("content", [])
    for block in content_blocks:
        if block.get("type") == "text":
            return block.get("text", "")

    frappe.throw(f"Unexpected Claude response format: {str(result)[:500]}")


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def parse_llm_response(raw_response):
    """Parse the JSON response from the LLM, handling common formatting issues."""
    text = raw_response.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)

    # Find JSON object boundaries
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        frappe.throw(
            f"Failed to parse LLM response as JSON: {str(e)}\n\nRaw response:\n{raw_response[:1000]}"
        )

    # Validate required fields
    for field in ["meta_title", "hero_headline", "sections"]:
        if field not in data:
            frappe.throw(f"LLM response missing required field: {field}")

    if not isinstance(data["sections"], list) or len(data["sections"]) == 0:
        frappe.throw("LLM response has no sections")

    valid_types = set(SECTION_TYPES)
    for i, section in enumerate(data["sections"]):
        if section.get("section_type") not in valid_types:
            data["sections"][i]["section_type"] = "Rich Text"

        items = section.get("items_json")
        if items and not isinstance(items, str):
            data["sections"][i]["items_json"] = json.dumps(items)

    return data
