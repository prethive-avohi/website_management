// CMS Template form — Template Administrator UI
frappe.ui.form.on("CMS Template", {
    refresh(frm) {
        _set_status_colour(frm);

        if (frm.is_new()) {
            // Pre-fill default prompt hint
            if (!frm.doc.ai_prompt) {
                frm.set_value("ai_prompt",
                    "Analyze the uploaded document and generate structured content JSON.\n\n" +
                    "Document text:\n{content}\n\n" +
                    "You must output JSON that exactly matches this schema:\n{schema}\n\n" +
                    "Rules:\n" +
                    "- Return ONLY valid JSON. No explanation, no markdown, no code fences.\n" +
                    "- Every field in the schema must be present in your output.\n" +
                    "- Keep text concise and professional.\n" +
                    "- For SEO fields: meta_title max 60 characters, meta_description max 160 characters.\n" +
                    "- Do not generate HTML, CSS, or Astro code — only JSON content values."
                );
            }
            return;
        }

        // ── Publish button (Draft → Active) ─────────────────────────────────
        if (frm.doc.status === "Draft") {
            frm.add_custom_button(__("Publish Template"), () => {
                if (!frm.doc.template_file) {
                    frappe.msgprint({
                        title: "Missing Template File",
                        message: "Upload an HTML or Astro template file before publishing.",
                        indicator: "orange",
                    });
                    return;
                }
                if (!frm.doc.json_schema) {
                    frappe.msgprint({
                        title: "Missing JSON Schema",
                        message: "Define a JSON schema before publishing.",
                        indicator: "orange",
                    });
                    return;
                }
                frappe.confirm(
                    "Publish this template? It will become available for all CMS users.",
                    () => {
                        frappe.call({
                            method: "pdcms_app.api.v1.templates.publish_template",
                            args: { name: frm.docname },
                            callback(r) {
                                if (r.message?.success) {
                                    frappe.show_alert({ message: "Template published.", indicator: "green" });
                                    frm.reload_doc();
                                }
                            },
                        });
                    }
                );
            }).addClass("btn-primary");
        }

        // ── Deprecate button (Active → Deprecated) ───────────────────────────
        if (frm.doc.status === "Active") {
            frm.add_custom_button(__("Deprecate"), () => {
                frappe.confirm("Deprecate this template? CMS users will no longer see it.", () => {
                    frm.set_value("status", "Deprecated");
                    frm.save();
                });
            });
        }

        // ── Validate Schema ──────────────────────────────────────────────────
        if (frm.doc.json_schema) {
            frm.add_custom_button(__("Validate Schema"), () => {
                try {
                    const parsed = JSON.parse(frm.doc.json_schema);
                    frappe.show_alert({ message: "JSON Schema is valid ✓", indicator: "green" });
                    // Show field count
                    const keys = parsed.properties ? Object.keys(parsed.properties) : [];
                    if (keys.length) {
                        frappe.show_alert({
                            message: `Top-level fields: ${keys.join(", ")}`,
                            indicator: "blue",
                        });
                    }
                } catch (e) {
                    frappe.show_alert({ message: "Invalid JSON: " + e.message, indicator: "red" });
                }
            });
        }

        // ── Test Preview ─────────────────────────────────────────────────────
        if (frm.doc.template_file) {
            frm.add_custom_button(__("Test Preview"), () => {
                // Build sample JSON from schema if available
                let sampleJson = "{}";
                if (frm.doc.json_schema) {
                    try {
                        const schema = JSON.parse(frm.doc.json_schema);
                        sampleJson = JSON.stringify(_schema_to_sample(schema), null, 2);
                    } catch (e) {
                        frappe.show_alert({ message: "Could not parse schema: " + e.message, indicator: "orange" });
                    }
                }

                frappe.prompt(
                    [{
                        fieldname: "sample_json",
                        fieldtype: "Code",
                        label: "Sample content_json",
                        options: "JSON",
                        reqd: 1,
                        default: sampleJson,
                    }],
                    (values) => {
                        try { JSON.parse(values.sample_json); }
                        catch (e) { frappe.msgprint("Invalid JSON: " + e.message); return; }

                        frappe.call({
                            method: "pdcms_app.api.v1.preview.render_template_test",
                            args: { template_name: frm.docname, content_json: values.sample_json },
                            callback(r) {
                                if (r.message) {
                                    const w = window.open("", "_blank");
                                    w.document.write(r.message);
                                    w.document.close();
                                }
                            },
                        });
                    },
                    __("Test Template Preview"),
                    __("Preview")
                );
            }, __("View"));
        }

        // ── View linked prompts ──────────────────────────────────────────────
        frm.add_custom_button(__("View Prompts"), () => {
            frappe.set_route("List", "CMS Prompt", { template: frm.docname });
        });
    },
});

function _set_status_colour(frm) {
    const map = { "Draft": "orange", "Active": "green", "Deprecated": "gray" };
    const colour = map[frm.doc.status] || "gray";
    frm.page.set_indicator(frm.doc.status, colour);
}

// Generate a sample JSON object from a JSON Schema for the test preview
function _schema_to_sample(schema) {
    if (!schema?.properties) return {};
    const result = {};
    for (const [key, def] of Object.entries(schema.properties)) {
        if (def.type === "object") {
            result[key] = _schema_to_sample(def);
        } else if (def.type === "array") {
            const itemSample = def.items ? _schema_to_sample(def.items) : "sample";
            result[key] = [itemSample];
        } else {
            result[key] = `[${key}]`;
        }
    }
    return result;
}
