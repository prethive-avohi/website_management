import requests
import frappe
from .base import BaseAIProvider


class OllamaProvider(BaseAIProvider):
    def __init__(self, url: str, model: str):
        self.url = url.rstrip("/")
        self.model = model

    def complete(self, prompt, system=None, temperature=0.3, max_tokens=8192) -> str:
        try:
            requests.get(f"{self.url}/api/tags", timeout=5).raise_for_status()
        except requests.exceptions.ConnectionError:
            frappe.throw(
                f"Cannot connect to Ollama at {self.url}. "
                "Run `ollama serve` or switch to a cloud provider in CMS Settings."
            )

        response = requests.post(
            f"{self.url}/api/generate",
            json={
                "model": self.model,
                "prompt": f"{self._system(system)}\n\n{prompt}",
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=300,
        )
        if response.status_code != 200:
            frappe.throw(f"Ollama error ({response.status_code}): {response.text[:500]}")
        return response.json().get("response", "")
