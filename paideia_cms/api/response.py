"""Standard API response envelope for all PDCMS v1 endpoints."""
import frappe


def success(data=None, meta=None) -> dict:
    return {
        "success": True,
        "data": data if data is not None else {},
        "meta": meta or {},
        "errors": [],
    }


def error(message: str, code: int = 400) -> dict:
    frappe.local.response["http_status_code"] = code
    return {
        "success": False,
        "data": {},
        "meta": {},
        "errors": [message],
    }


def not_found(resource: str) -> dict:
    return error(f"{resource} not found", code=404)
