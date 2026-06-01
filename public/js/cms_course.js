frappe.ui.form.on("CMS Course", {
    refresh(frm) {
        if (frm.is_new()) return;

        frm.add_custom_button(__("Preview"), () => {
            const url = `/api/method/pdcms_app.api.v1.preview.render_course?name=${encodeURIComponent(frm.docname)}`;
            window.open(url, "_blank");
        }, __("View"));

        frm.add_custom_button(__("Generate Content"), () => {
            if (!frm.doc.source_file) {
                frappe.msgprint("Please attach a source file (PDF or DOCX) first.");
                return;
            }
            frappe.confirm("Re-run AI generation? Existing content will be overwritten.", () => {
                frappe.call({
                    method: "pdcms_app.api.v1.admin.trigger_generation",
                    args: { doctype: "CMS Course", name: frm.docname },
                    callback(r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({ message: "Generation queued. Refresh in a moment.", indicator: "green" });
                            frm.reload_doc();
                        }
                    },
                });
            });
        }, __("AI"));
    },
});
