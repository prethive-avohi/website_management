frappe.ui.form.on("Paideia Bulk Content Generator", {
    refresh(frm) {
        // Generate All button — only if Draft or has pending items
        if (!frm.is_new() && frm.doc.status !== "Processing") {
            var has_pending = (frm.doc.files || []).some(function (row) {
                return row.item_status === "Pending";
            });

            if (has_pending || frm.doc.status === "Draft") {
                frm.add_custom_button(__("Generate All Pages"), function () {
                    var count = (frm.doc.files || []).filter(function (row) {
                        return row.item_status !== "Completed";
                    }).length;

                    frappe.confirm(
                        __("This will process {0} file(s) using AI to generate web pages. Continue?", [count]),
                        function () {
                            frappe.call({
                                method: "paideia_cms.paideia_cms.doctype.paideia_bulk_content_generator.paideia_bulk_content_generator.generate_all",
                                args: { docname: frm.doc.name },
                                freeze: true,
                                freeze_message: __("Processing files... This may take several minutes."),
                                callback: function (r) {
                                    if (r.message) {
                                        frappe.show_alert({
                                            message: __("Batch {0}: {1} processed, {2} failed", [
                                                r.message.status,
                                                r.message.processed,
                                                r.message.failed
                                            ]),
                                            indicator: r.message.failed > 0 ? "orange" : "green"
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
        }

        // Retry Failed button
        if (frm.doc.status === "Partially Failed") {
            var failed_count = (frm.doc.files || []).filter(function (row) {
                return row.item_status === "Failed";
            }).length;

            frm.add_custom_button(__("Retry {0} Failed", [failed_count]), function () {
                frappe.call({
                    method: "paideia_cms.paideia_cms.doctype.paideia_bulk_content_generator.paideia_bulk_content_generator.retry_failed",
                    args: { docname: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Retrying failed files..."),
                    callback: function (r) {
                        if (r.message) {
                            frappe.show_alert({
                                message: __("Retry complete: {0} processed, {1} failed", [
                                    r.message.processed,
                                    r.message.failed
                                ]),
                                indicator: r.message.failed > 0 ? "orange" : "green"
                            });
                            frm.reload_doc();
                        }
                    }
                });
            }, __("Actions")).addClass("btn-warning");
        }

        // Link to settings
        frm.add_custom_button(__("AI Settings"), function () {
            frappe.set_route("Form", "Paideia CMS Settings");
        }, __("Settings"));

        // Status indicator
        var colors = {
            "Draft": "blue",
            "Processing": "orange",
            "Completed": "green",
            "Partially Failed": "red"
        };
        if (frm.doc.status && colors[frm.doc.status]) {
            frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status]);
        }

        // Real-time progress listener
        frappe.realtime.on("bulk_content_progress", function (data) {
            if (data.docname === frm.doc.name) {
                frappe.show_alert({
                    message: __("[{0}/{1}] {2}: {3}", [
                        data.current, data.total,
                        data.file_title, data.item_status
                    ]),
                    indicator: data.item_status === "Completed" ? "green" : "red"
                });
            }
        });
    }
});

// Auto-fill title from filename when file is attached
frappe.ui.form.on("Paideia Bulk Upload Item", {
    source_file(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.source_file && !row.file_title) {
            // Extract filename without extension
            var parts = row.source_file.split("/");
            var filename = parts[parts.length - 1];
            filename = filename.replace(/\.[^/.]+$/, ""); // remove extension
            filename = filename.replace(/[_-]/g, " "); // clean up
            // Title case
            filename = filename.replace(/\b\w/g, function (l) { return l.toUpperCase(); });
            frappe.model.set_value(cdt, cdn, "file_title", filename);
        }
    },

    file_title(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.file_title && !row.slug) {
            var slug = row.file_title.toLowerCase()
                .replace(/[^a-z0-9\s-]/g, "")
                .replace(/\s+/g, "-")
                .replace(/-+/g, "-")
                .trim();
            frappe.model.set_value(cdt, cdn, "slug", slug);
        }
    }
});
