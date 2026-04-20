import json
import frappe
import requests


BLOCK_TYPES = [
    "Trust Strip", "Audience Cards", "Feature Cards", "Service Models",
    "Process Steps", "Testimonials", "CTA Banner", "Rich Text",
    "Scholarship List", "FAQ"
]

CONTENT_PROMPT = """You are a content extraction specialist. Read the document below and extract ALL its content into a series of blocks.

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "title": "Main title of the document",
  "blocks": [
    {{
      "type": "one of: Rich Text | Feature Cards | Process Steps | FAQ | Testimonials | CTA Banner | Trust Strip | Audience Cards | Service Models | Scholarship List",
      "heading": "Block heading (empty string if none)",
      "subheading": "Optional supporting text (empty string if none)",
      "body": "HTML body text for Rich Text blocks — use proper <p>, <ul>, <li>, <strong> tags. Empty string for other types.",
      "cta_label": "Call-to-action button label (empty string if none)",
      "cta_url": "Call-to-action URL (empty string if none)",
      "items": []
    }}
  ]
}}

Rules:
- items is a JSON array used for card/list/step/faq blocks. For Rich Text leave it as an empty array [].
- Feature Cards / Service Models / Audience Cards / Trust Strip / Testimonials items: [{{"title":"..","description":"..","icon":""}}]
- Process Steps items: [{{"step": 1, "title":"..","description":".."}}]
- FAQ items: [{{"question":"..","answer":".."}}]
- Scholarship List items: [{{"name":"..","amount":"..","eligibility":".."}}]
- CTA Banner has no items; use heading, body and cta_label/cta_url fields.
- Cover ALL content from the document — do not skip anything.
- Use as many blocks as needed (4–15) based on document length.

DOCUMENT TEXT:
{content}"""


def get_ai_settings():
    """Load AI provider settings from Paideia CMS Settings singleton."""
    settings = frappe.get_single("Paideia CMS Settings")
    return settings


def generate_page_content(extracted_text, page_type=None):
    """Route to the correct AI provider based on settings.

    Args:
        extracted_text: The text extracted from the document
        page_type: Unused — kept for call-site compatibility

    Returns:
        Parsed JSON dict with title and blocks list
    """
    settings = get_ai_settings()
    provider = settings.ai_provider

    prompt = CONTENT_PROMPT.format(content=extracted_text)

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
            "options": {"temperature": 0.3, "num_predict": 32768},
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
                "max_new_tokens": 16384,
                "temperature": 0.3,
                "return_full_text": False,
            },
        },
        timeout=180,
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

    # llama-3.3-70b-versatile supports up to 32768 output tokens
    # llama-3.1-8b-instant is capped at 8192 output tokens (too low for full pages)
    model = settings.groq_model or "llama-3.3-70b-versatile"

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
            "max_tokens": 32768,
        },
        timeout=180,
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
            "max_tokens": 16384,
            "response_format": {"type": "json_object"},
        },
        timeout=180,
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
            "max_tokens": 32000,
            "system": "You are a web content generator. Return ONLY valid JSON, no markdown fences, no explanation.",
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        },
        timeout=300,
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

    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)

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

    if "blocks" not in data or not isinstance(data["blocks"], list) or len(data["blocks"]) == 0:
        frappe.throw("LLM response missing 'blocks' array")

    valid_types = set(BLOCK_TYPES)
    for i, block in enumerate(data["blocks"]):
        if block.get("type") not in valid_types:
            data["blocks"][i]["type"] = "Rich Text"

        items = block.get("items")
        if items is not None and not isinstance(items, list):
            try:
                data["blocks"][i]["items"] = json.loads(items)
            except (ValueError, TypeError):
                data["blocks"][i]["items"] = []

    return data
