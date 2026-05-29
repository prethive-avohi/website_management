import requests
import frappe
from .base import BaseAIProvider


class GroqProvider(BaseAIProvider):
    _API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete(self, prompt, system=None, temperature=0.3, max_tokens=8192) -> str:
        response = requests.post(
            self._API_URL,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._system(system)},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=180,
        )
        if response.status_code == 429:
            frappe.throw("Groq rate limit exceeded. Please wait and retry.")
        if response.status_code != 200:
            frappe.throw(f"Groq API error ({response.status_code}): {response.text[:500]}")
        return response.json()["choices"][0]["message"]["content"]
