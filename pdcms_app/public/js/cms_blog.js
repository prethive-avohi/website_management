frappe.ui.form.on("CMS Blog", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Generate Content"), () => {
                frappe.confirm("Re-run AI generation? Existing content will be overwritten.", () => {
                    frappe.call({
                        method: "pdcms_app.api.v1.admin.trigger_generation",
                        args: { doctype: "CMS Blog", name: frm.docname },
                        callback(r) {
                            if (r.message && r.message.success) {
                                frappe.show_alert({ message: "Generation queued.", indicator: "green" });
                                frm.reload_doc();
                            }
                        },
                    });
                });
            }, __("AI"));
        }
    },
});
