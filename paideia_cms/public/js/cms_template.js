// CMS Template form — Template Administrator UI
frappe.ui.form.on("CMS Template", {
    refresh(frm) {
        _set_status_colour(frm);

        if (frm.is_new()) {
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

        // Always sync Test Preview localStorage from sample_content_json
        if (frm.doc.sample_content_json) {
            const previewKey = `pdcms_preview_json::${frm.docname}`;
            localStorage.setItem(previewKey, frm.doc.sample_content_json);
        }

        frm.add_custom_button(__("Publish Template"), () => {
            if (!frm.doc.template_file) {
                frappe.msgprint({ title: "Missing Template File", message: "Upload an HTML template file before publishing.", indicator: "orange" });
                return;
            }
            if (!frm.doc.json_schema) {
                frappe.msgprint({ title: "Missing JSON Schema", message: "Define a JSON schema before publishing.", indicator: "orange" });
                return;
            }
            if (frm.doc.status === "Active") {
                frappe.msgprint({ title: "Already Published", message: "This template is already Active.", indicator: "blue" });
                return;
            }
            frappe.confirm("Publish this template? It will become available for all CMS users.", () => {
                frappe.call({
                    method: "paideia_cms.api.v1.templates.publish_template",
                    args: { name: frm.docname },
                    callback(r) {
                        if (r.message?.success) {
                            frappe.show_alert({ message: "Template published.", indicator: "green" });
                            frm.reload_doc();
                        }
                    },
                });
            });
        }).addClass("btn-primary");

        frm.add_custom_button(__("Deprecate"), () => {
            frappe.confirm("Deprecate this template? CMS users will no longer see it.", () => {
                frm.set_value("status", "Deprecated");
                frm.save();
            });
        });

        frm.add_custom_button(__("Validate Schema"), () => {
            if (!frm.doc.json_schema) {
                frappe.msgprint({ title: "No Schema", message: "Paste a JSON schema first.", indicator: "orange" });
                return;
            }
            try {
                const parsed = JSON.parse(frm.doc.json_schema);
                frappe.show_alert({ message: "JSON Schema is valid ✓", indicator: "green" });
                const keys = parsed.properties ? Object.keys(parsed.properties) : [];
                if (keys.length) frappe.show_alert({ message: `Top-level fields: ${keys.join(", ")}`, indicator: "blue" });
            } catch (e) {
                frappe.show_alert({ message: "Invalid JSON: " + e.message, indicator: "red" });
            }
        });

        frm.add_custom_button(__("Test Preview"), () => {
            if (!frm.doc.template_file) {
                frappe.msgprint({ title: "No Template File", message: "Upload a template file first.", indicator: "orange" });
                return;
            }
            const _storageKey = `pdcms_preview_json::${frm.docname}`;
            let sampleJson = localStorage.getItem(_storageKey) || "{}";

            if (sampleJson === "{}" && frm.doc.json_schema) {
                try {
                    const parsed = JSON.parse(frm.doc.json_schema);
                    const sample = _schema_to_sample(parsed);
                    if (Object.keys(sample).length) sampleJson = JSON.stringify(sample, null, 2);
                } catch (e) { }
            }

            frappe.prompt(
                [{ fieldname: "sample_json", fieldtype: "Code", label: "Content JSON (saved per template)", options: "JSON", reqd: 1, default: sampleJson }],
                (values) => {
                    try { JSON.parse(values.sample_json); }
                    catch (e) { frappe.msgprint("Invalid JSON: " + e.message); return; }

                    localStorage.setItem(_storageKey, values.sample_json);
                    const previewWin = window.open("", "_blank");
                    if (!previewWin) {
                        frappe.msgprint({ title: "Popup Blocked", message: "Allow popups for this site.", indicator: "orange" });
                        return;
                    }
                    previewWin.document.write("Loading preview…");
                    frappe.call({
                        method: "paideia_cms.api.v1.preview.render_template_test",
                        args: { template_name: frm.docname, content_json: values.sample_json },
                        callback(r) {
                            if (r.message) {
                                previewWin.document.open();
                                previewWin.document.write(r.message);
                                previewWin.document.close();
                            } else {
                                previewWin.document.write("<p>No content returned.</p>");
                                previewWin.document.close();
                            }
                        },
                        error() {
                            previewWin.document.write("<p>Server error. Check console.</p>");
                            previewWin.document.close();
                        }
                    });
                },
                __("Test Template Preview"),
                __("Preview")
            );
        });

        frm.add_custom_button(__("View Prompts"), () => {
            frappe.set_route("List", "CMS Prompt", { template: frm.docname });
        });

        if (frm.doc.astro_component) {
            _validate_astro_component(frm);
        }
    },

    astro_component(frm) {
        if (frm.doc.astro_component) _validate_astro_component(frm);
    },
});

// ── Helpers ──────────────────────────────────────────────────────────────

async function _validate_astro_component(frm) {
    const r = await frappe.call({
        method: "paideia_cms.api.v1.registry.get_template_registry",
        args: {},
    });
    const components = r?.message?.data || [];
    const known = components.map(c => c.astro_component);
    const val = frm.doc.astro_component;
    if (!known.length) return; // registry unreadable — skip
    if (!known.includes(val)) {
        frm.set_df_property("astro_component", "description",
            `⚠ "${val}" is not in TEMPLATE_REGISTRY.json. Known: ${known.join(", ")}`);
    } else {
        const entry = components.find(c => c.astro_component === val);
        frm.set_df_property("astro_component", "description",
            `✓ Registered — ${entry.description}`);
    }
}

function _set_status_colour(frm) {
    const map = { "Draft": "orange", "Active": "green", "Deprecated": "gray" };
    frm.page.set_indicator(frm.doc.status, map[frm.doc.status] || "gray");
}

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
