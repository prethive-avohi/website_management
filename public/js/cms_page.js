frappe.ui.form.on("CMS Page", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Generate Content"), () => {
                frappe.confirm(
                    "Re-run AI generation? Existing content will be overwritten.",
                    () => {
                        frappe.call({
                            method: "pdcms_app.api.v1.admin.trigger_generation",
                            args: { doctype: "CMS Page", name: frm.docname },
                            callback(r) {
                                if (r.message && r.message.success) {
                                    frappe.show_alert({ message: "Generation queued.", indicator: "green" });
                                    frm.reload_doc();
                                }
                            },
                        });
                    }
                );
            }, __("AI"));

            if (frm.doc.content_json) {
                frm.add_custom_button(__("Trigger Translation"), () => {
                    frappe.prompt(
                        [{ fieldname: "language", fieldtype: "Data", label: "Language Code (e.g. ar, fr)", reqd: 1 }],
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
        }
    },
});
