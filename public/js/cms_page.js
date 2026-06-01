frappe.ui.form.on("CMS Page", {
    refresh(frm) {
        if (frm.is_new()) return;

        // Preview button — always shown if template file exists
        frm.add_custom_button(__("Preview"), () => {
            const url = `/api/method/pdcms_app.api.v1.preview.render_page?name=${encodeURIComponent(frm.docname)}`;
            window.open(url, "_blank");
        }, __("View"));

        // Generate Content
        frm.add_custom_button(__("Generate Content"), () => {
            if (!frm.doc.source_file) {
                frappe.msgprint("Please attach a source file (PDF or DOCX) first.");
                return;
            }
            if (!frm.doc.template) {
                frappe.msgprint("Please select a template first.");
                return;
            }
            frappe.confirm(
                "Re-run AI generation? Existing content will be overwritten.",
                () => {
                    frappe.call({
                        method: "pdcms_app.api.v1.admin.trigger_generation",
                        args: { doctype: "CMS Page", name: frm.docname },
                        callback(r) {
                            if (r.message && r.message.success) {
                                frappe.show_alert({ message: "Generation queued. Refresh in a moment.", indicator: "green" });
                                frm.reload_doc();
                            }
                        },
                    });
                }
            );
        }, __("AI"));

        // Trigger Translation
        if (frm.doc.content_json) {
            frm.add_custom_button(__("Translate"), () => {
                frappe.prompt(
                    [{ fieldname: "language", fieldtype: "Data", label: "Language Code (e.g. ar, fr, ta)", reqd: 1 }],
                    (values) => {
                        frappe.call({
                            method: "pdcms_app.api.v1.admin.trigger_translation",
                            args: { doctype: "CMS Page", name: frm.docname, language: values.language },
                            callback(r) {
                                if (r.message && r.message.success) {
                                    frappe.show_alert({ message: "Translation queued.", indicator: "green" });
                                }
                            },
                        });
                    },
                    __("Translate to Language"),
                    __("Queue")
                );
            }, __("AI"));
        }

        // Colour generation_status indicator
        _set_status_indicator(frm);
    },
});

function _set_status_indicator(frm) {
    const status = frm.doc.generation_status;
    const map = {
        "Pending":    "gray",
        "Queued":     "orange",
        "Extracting": "blue",
        "Generating": "blue",
        "Completed":  "green",
        "Failed":     "red",
    };
    const colour = map[status] || "gray";
    frm.set_indicator_formatter("generation_status", () => colour);
}
