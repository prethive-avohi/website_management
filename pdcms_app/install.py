import frappe


def after_install():
    _create_roles()
    _create_default_settings()
    frappe.db.commit()


def after_migrate():
    _create_roles()
    frappe.db.commit()


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

_ROLES = ["CMS Admin", "Content Editor", "CMS Reviewer", "CMS Publisher"]


def _create_roles():
    for role_name in _ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Default singleton settings
# ---------------------------------------------------------------------------

def _create_default_settings():
    if not frappe.db.exists("DocType", "CMS Settings"):
        return

    settings = frappe.get_single("CMS Settings")
    if settings.ai_provider:
        return

    import os
    is_cloud = bool(
        os.environ.get("FC_SITE")
        or os.environ.get("FRAPPE_CLOUD")
        or os.path.exists("/home/frappe/frappe-bench/.cloud")
    )

    settings.ai_provider = "Groq" if is_cloud else "Ollama"
    settings.ollama_url = "http://localhost:11434"
    settings.ollama_model = "mistral"
    settings.groq_model = "llama-3.3-70b-versatile"
    settings.openai_model = "gpt-4o-mini"
    settings.claude_model = "claude-sonnet-4-6"
    settings.translation_provider = "None"
    settings.api_cache_ttl = 300
    settings.save(ignore_permissions=True)
