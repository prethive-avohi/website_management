frappe.ui.form.on("CMS Template", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("View Prompts"), () => {
                frappe.set_route("List", "CMS Prompt", { template: frm.docname });
            });
        }

        if (frm.doc.json_schema) {
            frm.add_custom_button(__("Validate Schema JSON"), () => {
                try {
                    JSON.parse(frm.doc.json_schema);
                    frappe.show_alert({ message: "JSON Schema is valid.", indicator: "green" });
                } catch (e) {
                    frappe.show_alert({ message: "Invalid JSON: " + e.message, indicator: "red" });
                }
            });
        }
    },
});
