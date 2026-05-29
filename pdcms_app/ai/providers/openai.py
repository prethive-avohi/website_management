import json
import requests
import frappe
from .base import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    _API_URL = "https://api.openai.com/v1/chat/completions"

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
                "response_format": {"type": "json_object"},
                "stream": True,
            },
            timeout=(30, 60),
            stream=True,
        )
        if response.status_code == 401:
            frappe.throw("Invalid OpenAI API key.")
        if response.status_code == 429:
            frappe.throw("OpenAI rate limit exceeded.")
        if response.status_code != 200:
            frappe.throw(f"OpenAI error ({response.status_code}): {response.text[:500]}")

        chunks = []
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8") if isinstance(line, bytes) else line
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                    delta = event["choices"][0]["delta"]
                    if "content" in delta and delta["content"]:
                        chunks.append(delta["content"])
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        return "".join(chunks)
