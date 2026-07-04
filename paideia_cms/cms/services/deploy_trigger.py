"""
Frontend deploy trigger — fires the Vercel deploy hook when published content changes.

The Astro frontend is statically built (getStaticPaths fetches all slugs from the
guest API at build time). New or changed content only goes live after a rebuild,
so publishing a CMS Page/Blog/Course triggers one via the Vercel deploy hook.

Debounced to one trigger per DEBOUNCE_SECONDS window — a flurry of publishes in
quick succession results in a single rebuild, not one per document.
"""
import frappe
from paideia_cms.logger import get_logger

log = get_logger("deploy_trigger")

DEBOUNCE_SECONDS = 60
_DEBOUNCE_CACHE_KEY = "pdcms:vercel_deploy:debounce"


def trigger_deploy(reason: str = "") -> None:
    """Fire the Vercel deploy hook, debounced. Safe to call on every publish."""
    settings = frappe.get_cached_doc("CMS Settings")
    hook_url = settings.get_password("vercel_deploy_hook_url", raise_exception=False) or ""
    if not hook_url:
        return

    cache = frappe.cache()
    if cache.get_value(_DEBOUNCE_CACHE_KEY):
        log.debug("Deploy trigger skipped (debounced) — reason: %s", reason)
        return
    cache.set_value(_DEBOUNCE_CACHE_KEY, "1", expires_in_sec=DEBOUNCE_SECONDS)

    frappe.enqueue(
        "paideia_cms.cms.services.deploy_trigger._post_deploy_hook",
        queue="short",
        hook_url=hook_url,
        reason=reason,
    )


def _post_deploy_hook(hook_url: str, reason: str = "") -> None:
    import requests
    try:
        requests.post(hook_url, timeout=15)
        log.info("Vercel deploy triggered — %s", reason)
    except Exception as e:
        log.warning("Vercel deploy trigger failed — %s", e)
