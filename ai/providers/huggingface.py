import requests
import frappe
from .base import BaseAIProvider


class HuggingFaceProvider(BaseAIProvider):
    def __init__(self, api_token: str, model: str):
        self.api_token = api_token
        self.model = model

    def complete(self, prompt, system=None, temperature=0.3, max_tokens=8192) -> str:
        full_prompt = f"{self._system(system)}\n\n{prompt}"
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{self.model}",
            headers={"Authorization": f"Bearer {self.api_token}"},
            json={
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "return_full_text": False,
                },
            },
            timeout=180,
        )
        if response.status_code == 503:
            frappe.throw("HuggingFace model is loading (cold start). Retry in 30-60 seconds.")
        if response.status_code != 200:
            frappe.throw(f"HuggingFace error ({response.status_code}): {response.text[:500]}")
        result = response.json()
        if isinstance(result, list) and result:
            return result[0].get("generated_text", "")
        frappe.throw(f"Unexpected HuggingFace response: {str(result)[:500]}")
