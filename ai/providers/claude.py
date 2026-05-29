import requests
import frappe
from .base import BaseAIProvider


class ClaudeProvider(BaseAIProvider):
    _API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete(self, prompt, system=None, temperature=0.3, max_tokens=8192) -> str:
        response = requests.post(
            self._API_URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "system": self._system(system),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            },
            timeout=300,
        )
        if response.status_code == 401:
            frappe.throw("Invalid Anthropic API key.")
        if response.status_code == 429:
            frappe.throw("Anthropic rate limit exceeded.")
        if response.status_code != 200:
            frappe.throw(f"Claude API error ({response.status_code}): {response.text[:500]}")

        result = response.json()
        for block in result.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "")
        frappe.throw(f"Unexpected Claude response: {str(result)[:500]}")
