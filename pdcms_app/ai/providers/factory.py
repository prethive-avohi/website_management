import frappe
from .base import BaseAIProvider


def get_provider() -> BaseAIProvider:
    """Load active AI provider from CMS Settings and return a configured instance."""
    settings = frappe.get_single("CMS Settings")
    provider = settings.ai_provider

    if provider == "Ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(
            url=settings.ollama_url or "http://localhost:11434",
            model=settings.ollama_model or "mistral",
        )
    if provider == "Groq":
        from .groq import GroqProvider
        return GroqProvider(
            api_key=settings.get_password("groq_api_key") or "",
            model=settings.groq_model or "llama-3.3-70b-versatile",
        )
    if provider == "OpenAI":
        from .openai import OpenAIProvider
        return OpenAIProvider(
            api_key=settings.get_password("openai_api_key") or "",
            model=settings.openai_model or "gpt-4o-mini",
        )
    if provider == "HuggingFace":
        from .huggingface import HuggingFaceProvider
        return HuggingFaceProvider(
            api_token=settings.get_password("hf_api_token") or "",
            model=settings.hf_model or "mistralai/Mistral-7B-Instruct-v0.3",
        )
    if provider == "Claude":
        from .claude import ClaudeProvider
        return ClaudeProvider(
            api_key=settings.get_password("claude_api_key") or "",
            model=settings.claude_model or "claude-sonnet-4-6",
        )

    frappe.throw(f"Unknown AI provider configured: {provider}")
