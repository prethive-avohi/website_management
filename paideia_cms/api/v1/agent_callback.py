"""
Agent service callback endpoint.

The external paideia-agents service POSTs results here as a job progresses.
Auth via X-Agent-Secret header (shared secret from CMS Settings).

Payload shapes:

  Step:
    { "job_id": "...", "status": "step", "message": "...", "context": { "doctype": "...", "doc_name": "..." } }

  Completed:
    { "job_id": "...", "status": "completed", "content_json": {...}, "metadata": {...}, "context": {...} }

  Failed:
    { "job_id": "...", "status": "failed", "error": "...", "context": {...} }
"""
import json
import frappe
from paideia_cms.logger import get_logger
log = get_logger("agent_callback")


@frappe.whitelist(allow_guest=True)
def receive():
    _verify_secret()

    data   = frappe.request.get_json(silent=True) or {}
    status = data.get("status")
    job_id = data.get("job_id", "?")

    log.debug("Callback received — job=%s  status=%s", job_id, status)

    if status == "step":
        _handle_step(data)
    elif status == "completed":
        _handle_completed(data)
    elif status == "failed":
        _handle_failed(data)
    else:
        frappe.throw(f"Unknown callback status: '{status}'")

    return {"ok": True}


# ── Handlers ───────────────────────────────────────────────────────────────

def _handle_step(data: dict):
    message = data.get("message", "")
    ctx     = data.get("context") or {}
    log.debug("  → Step: %s", message)

    doctype  = ctx.get("doctype")
    doc_name = ctx.get("doc_name")
    if doctype and doc_name:
        frappe.db.set_value(doctype, doc_name, "generation_status", message[:140])
        frappe.db.commit()


def _handle_completed(data: dict):
    ctx          = data.get("context") or {}
    doctype      = ctx.get("doctype")
    doc_name     = ctx.get("doc_name")
    content_json = data.get("content_json", {})
    metadata     = data.get("metadata", {})

    if not doctype or not doc_name:
        log.warning("Completed callback missing context — job=%s", data.get("job_id", "?"))
        return

    log.debug("Saving content_json to %s '%s' — %d top-level keys, %s tokens",
              doctype, doc_name, len(content_json), metadata.get("tokens_used", "?"))

    frappe.db.set_value(doctype, doc_name, "content_json",
                        json.dumps(content_json, indent=2))
    frappe.db.set_value(doctype, doc_name, "generation_status", "Completed")

    ai_job = frappe.db.get_value(doctype, doc_name, "ai_job")
    if ai_job:
        frappe.db.set_value("AI Job Log", ai_job, "status", "Completed")
        frappe.db.set_value("AI Job Log", ai_job, "completed_at", frappe.utils.now())

    log.debug("Content generation complete ✓ — %s '%s'", doctype, doc_name)
    frappe.db.commit()


def _handle_failed(data: dict):
    ctx      = data.get("context") or {}
    doctype  = ctx.get("doctype")
    doc_name = ctx.get("doc_name")
    error    = data.get("error", "Unknown error from agent service.")

    log.warning("Agent job failed — job=%s  error: %s", data.get("job_id", "?"), error[:200])

    if doctype and doc_name:
        frappe.db.set_value(doctype, doc_name, "generation_status", "Failed")
        frappe.db.set_value(doctype, doc_name, "ai_error_log", error[:10000])
        ai_job = frappe.db.get_value(doctype, doc_name, "ai_job")
        if ai_job:
            frappe.db.set_value("AI Job Log", ai_job, "status", "Failed")
        frappe.db.commit()


# ── Auth ───────────────────────────────────────────────────────────────────

def _verify_secret():
    incoming = frappe.request.headers.get("X-Agent-Secret", "")
    expected = frappe.get_single("CMS Settings").get_password("agent_service_secret", raise_exception=False) or ""

    if not expected:
        frappe.throw("Agent service secret not configured in CMS Settings.", frappe.PermissionError)
    if incoming != expected:
        frappe.throw("Invalid agent secret.", frappe.PermissionError)
