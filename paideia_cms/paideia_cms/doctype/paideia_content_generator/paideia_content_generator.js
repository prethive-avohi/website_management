frappe.ui.form.on("Paideia Content Generator", {
    refresh(frm) {
        var status = frm.doc.status;

        if (!frm.is_new() && status !== "Completed") {
            frm.add_custom_button(__("Generate Page"), function () {
                frappe.confirm(
                    __(
                        "This will extract content from the uploaded document and generate " +
                        "structured blocks using AI. Provider configured in Paideia CMS Settings. Continue?"
                    ),
                    function () {
                        frappe.call({
                            method: "paideia_cms.paideia_cms.doctype.paideia_content_generator.paideia_content_generator.generate_page",
                            args: { docname: frm.doc.name },
                            callback: function (r) {
                                if (r.message && r.message.status === "queued") {
                                    frappe.show_alert({
                                        message: __("Generation started in background. This page will refresh automatically."),
                                        indicator: "blue"
                                    });
                                    frm._poll_generation();
                                }
                            }
                        });
                    }
                );
            }, __("Actions"));
        }

        // Reset button for stuck records
        if (!frm.is_new() && (status === "Extracting" || status === "Generating")) {
            frm.add_custom_button(__("Reset Status"), function () {
                frappe.call({
                    method: "paideia_cms.paideia_cms.doctype.paideia_content_generator.paideia_content_generator.reset_status",
                    args: { docname: frm.doc.name },
                    callback: function () {
                        frm.reload_doc();
                    }
                });
            }, __("Actions"));

            // Auto-poll while in-progress
            frm._poll_generation();
        }

        frm.add_custom_button(__("AI Settings"), function () {
            frappe.set_route("Form", "Paideia CMS Settings");
        }, __("Settings"));

        var colors = {
            "Completed": "green",
            "Failed": "red",
            "Generating": "orange",
            "Extracting": "orange",
            "Pending": "blue"
        };
        if (status && colors[status]) {
            frm.page.set_indicator(__(status), colors[status]);
        }
    },

    title(frm) {
        if (frm.doc.title && !frm.doc.slug) {
            frm.set_value("slug", frm.doc.title.toLowerCase()
                .replace(/[^a-z0-9\s-]/g, "")
                .replace(/\s+/g, "-")
                .replace(/-+/g, "-")
                .trim());
        }
    }
});

// Poll every 4 seconds until status leaves Extracting/Generating
frappe.ui.form.on("Paideia Content Generator", {
    onload(frm) {
        frm._poll_generation = function () {
            if (frm._poller) return;
            frm._poller = setInterval(function () {
                frappe.db.get_value(
                    "Paideia Content Generator",
                    frm.doc.name,
                    "status",
                    function (val) {
                        var s = val && val.status;
                        if (s !== "Extracting" && s !== "Generating") {
                            clearInterval(frm._poller);
                            frm._poller = null;
                            frm.reload_doc();
                        }
                    }
                );
            }, 4000);
        };
    }
});
