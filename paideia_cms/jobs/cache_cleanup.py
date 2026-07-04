import frappe
from paideia_cms.cms.services.cache_service import invalidate_all


def evict_expired():
    """
    Hourly scheduled job — clears all pdcms:* cache keys.
    Redis TTL handles per-key expiry; this is a safety net for stale entries
    that survive across bench restarts or long-lived connections.
    """
    invalidate_all()
    frappe.logger().info("pdcms: hourly cache flush complete")
