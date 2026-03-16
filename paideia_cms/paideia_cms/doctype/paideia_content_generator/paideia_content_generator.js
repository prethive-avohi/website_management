frappe.ui.form.on("Paideia Content Generator", {
    refresh(frm) {
        // Show Generate Page button when saved and not yet completed
        if (!frm.is_new() && frm.doc.status !== "Completed") {
            frm.add_custom_button(__("Generate Page"), function () {
                frappe.confirm(
                    __(
                        "This will extract content from the uploaded document and generate a web page using AI. " +
                        "Provider configured in Paideia CMS Settings. Continue?"
                    ),
                    function () {
                        frappe.call({
                            method: "paideia_cms.paideia_cms.doctype.paideia_content_generator.paideia_content_generator.generate_page",
                            args: { docname: frm.doc.name },
                            freeze: true,
                            freeze_message: __("Extracting content and generating page... This may take a minute."),
                            callback: function (r) {
                                if (r.message && r.message.status === "success") {
                                    frappe.show_alert({
                                        message: __("Page generated successfully! Slug: {0}", [r.message.slug]),
                                        indicator: "green"
                                    });
                                    frm.reload_doc();
                                }
                            },
                            error: function () {
                                frm.reload_doc();
                            }
                        });
                    }
                );
            }, __("Actions")).addClass("btn-primary");
        }

        // Link to generated page
        if (frm.doc.generated_page) {
            frm.add_custom_button(__("View Generated Page"), function () {
                frappe.set_route("Form", "Paideia Web Page", frm.doc.generated_page);
            }, __("Actions"));
        }

        // Link to settings
        frm.add_custom_button(__("AI Settings"), function () {
            frappe.set_route("Form", "Paideia CMS Settings");
        }, __("Settings"));

        // Status indicator
        var colors = {
            "Completed": "green",
            "Failed": "red",
            "Generating": "orange",
            "Extracting": "orange",
            "Pending": "blue"
        };
        if (frm.doc.status && colors[frm.doc.status]) {
            frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status]);
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
