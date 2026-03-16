import subprocess
import frappe


def after_install():
    """Run after app install: install Python dependencies and set up defaults."""
    _install_pip_dependencies()
    _create_default_settings()
    frappe.db.commit()


def _install_pip_dependencies():
    """Install required Python packages via pip."""
    packages = ["PyPDF2", "python-docx"]
    for pkg in packages:
        try:
            subprocess.check_call(
                ["pip", "install", "--quiet", pkg],
                timeout=120,
            )
            print(f"  Installed {pkg}")
        except Exception as e:
            print(f"  Warning: Could not install {pkg}: {e}")
            print(f"  Run manually: bench pip install {pkg}")


def _create_default_settings():
    """Ensure Paideia CMS Settings singleton exists with sensible defaults."""
    if not frappe.db.exists("DocType", "Paideia CMS Settings"):
        return

    settings = frappe.get_single("Paideia CMS Settings")

    if not settings.ai_provider:
        # Detect environment: Frappe Cloud sets FC_SITE or similar env vars
        import os
        is_cloud = bool(
            os.environ.get("FC_SITE")
            or os.environ.get("FRAPPE_CLOUD")
            or os.path.exists("/home/frappe/frappe-bench/.cloud")
        )

        if is_cloud:
            settings.ai_provider = "Groq (Free API)"
            settings.setup_status = (
                "## Frappe Cloud Detected\n\n"
                "Ollama cannot run on Frappe Cloud. Choose a cloud provider:\n\n"
                "### Free Options:\n"
                "- **Groq** (default) — Get free key at console.groq.com/keys\n"
                "- **HuggingFace** — Get free token at huggingface.co/settings/tokens\n\n"
                "### Paid Options (best quality):\n"
                "- **OpenAI (ChatGPT)** — Get key at platform.openai.com/api-keys\n"
                "- **Claude (Anthropic)** — Get key at console.anthropic.com/settings/keys\n"
            )
        else:
            settings.ai_provider = "Ollama (Local)"
            settings.setup_status = (
                "## Local / Self-Hosted Setup\n\n"
                "Using **Ollama (Local)** as default (free, unlimited).\n\n"
                "### Ollama Setup:\n"
                "1. Install: `brew install ollama` or visit ollama.ai\n"
                "2. Pull model: `ollama pull mistral`\n"
                "3. Start: `ollama serve`\n\n"
                "### Cloud Alternatives:\n"
                "- **Groq / HuggingFace** — Free cloud APIs\n"
                "- **OpenAI (ChatGPT)** — Paid, platform.openai.com/api-keys\n"
                "- **Claude (Anthropic)** — Paid, console.anthropic.com/settings/keys\n"
            )

        settings.save(ignore_permissions=True)

    print("  Paideia CMS Settings initialized")
