import frappe
from frappe.model.document import Document


class AIJobLog(Document):
    def mark_running(self):
        self.db_set("status", "Running")
        self.db_set("started_at", frappe.utils.now())

    def mark_completed(self, raw_response: str = ""):
        import time
        started = frappe.utils.get_datetime(self.started_at)
        duration = (frappe.utils.now_datetime() - started).total_seconds() if started else 0
        self.db_set("status", "Completed")
        self.db_set("completed_at", frappe.utils.now())
        self.db_set("duration_seconds", round(duration, 2))
        if raw_response:
            self.db_set("raw_response", raw_response[:50000])

    def mark_failed(self, error: str):
        self.db_set("status", "Failed")
        self.db_set("completed_at", frappe.utils.now())
        self.db_set("error_trace", error[:10000])
