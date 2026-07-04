frappe.ui.form.on("CMS Page", {
    refresh(frm) {
        if (frm.is_new()) return;

        _toggle_content_field(frm);
        _render_generation_banner(frm);
        _set_primary_action(frm);
        _add_menu_buttons(frm);
        _set_status_colour(frm);
        _render_image_slots(frm);

        if (_is_generating(frm)) {
            _start_polling(frm);
        }
    },

    onload(frm) {
        if (!frm.is_new() && _is_generating(frm)) {
            _start_polling(frm);
        }
    },

    template(frm) {
        if (!frm.is_new()) _render_image_slots(frm);
    },
});

// ── Hide content_json until content exists ───────────────────────────────────

function _toggle_content_field(frm) {
    const hasContent = !!(frm.doc.content_json && frm.doc.content_json.trim() !== "{}");
    frm.set_df_property("content_json", "hidden", !hasContent);
}

// ── Primary action button ────────────────────────────────────────────────────

function _set_primary_action(frm) {
    frm.page.clear_primary_action();
    frm.page.clear_secondary_action();

    if (frm.doc.content_json && frm.doc.workflow_state !== "Published") {
        frm.page.set_primary_action(__("Publish"), () => {
            _publish(frm);
        }, "globe");
    } else if (!frm.doc.content_json && frm.doc.source_file && !_is_generating(frm)) {
        frm.page.set_primary_action(__("Generate Content"), () => {
            _trigger_generation(frm);
        }, "play");
    }
}

// ── Banner shown while AI is running ────────────────────────────────────────

function _render_generation_banner(frm) {
    frm.dashboard.clear_headline();
    const status = frm.doc?.generation_status;

    const spinner = `<div class="spinner-border spinner-border-sm text-primary" role="status"></div>`;
    const banners = {
        "Queued":     ["yellow", `<div class="d-flex align-items-center gap-2">${spinner}<span><b>Queued.</b> AI generation will start shortly.</span></div>`],
        "Extracting": ["yellow", `<div class="d-flex align-items-center gap-2">${spinner}<span><b>Extracting text</b> from your document…</span></div>`],
        "Generating": ["yellow", `<div class="d-flex align-items-center gap-2">${spinner}<span><b>Generating content</b> — AI is working. This page will refresh automatically.</span></div>`],
        "Completed":  ["green",  `<span>✓ <b>Content generated.</b> Review below then click <b>Preview</b>.</span>`],
        "Failed":     ["red",    `<span>✗ <b>Generation failed.</b> Fix the issue and click <b>Generate Content</b> to retry.</span>`],
    };

    // Also show agent step messages
    const generatingStatuses = ["Queued", "Extracting", "Generating"];
    if (!banners[status] && status && !["Completed", "Failed"].includes(status)) {
        frm.dashboard.set_headline_alert(
            `<div class="d-flex align-items-center gap-2">${spinner}<span><b>${status}</b></span></div>`,
            "yellow"
        );
        return;
    }

    const banner = banners[status];
    if (banner) frm.dashboard.set_headline_alert(banner[1], banner[0]);
}

// ── Poll every 4 seconds while generating ───────────────────────────────────

function _start_polling(frm) {
    if (frm._cms_poll_timer) return;

    frm._cms_poll_timer = setInterval(() => {
        frappe.db.get_value("CMS Page", frm.docname, "generation_status")
            .then(r => {
                const status = r.message?.generation_status;
                if (!status) return;
                if (_is_generating_status(status)) {
                    frm.doc.generation_status = status;
                    _render_generation_banner(frm);
                } else {
                    clearInterval(frm._cms_poll_timer);
                    frm._cms_poll_timer = null;
                    frm.reload_doc();
                }
            });
    }, 4000);
}

// ── Menu buttons ─────────────────────────────────────────────────────────────

function _add_menu_buttons(frm) {
    if (frm.doc.content_json) {
        frm.add_custom_button(__("Preview"), () => {
            window.open(`/api/method/paideia_cms.api.v1.preview.render_page?name=${encodeURIComponent(frm.docname)}`, "_blank");
        }, __("View"));

        if (frm.doc.workflow_state === "Published") {
            frm.add_custom_button(__("Unpublish"), () => {
                _set_workflow_state(frm, "Draft");
            }, __("View"));
        }

        frm.add_custom_button(__("Re-generate"), () => {
            _trigger_generation(frm);
        }, __("AI"));

        frm.add_custom_button(__("Translate"), () => {
            frappe.prompt(
                [{ fieldname: "language", fieldtype: "Data", label: "Language Code (e.g. ar, fr, ta)", reqd: 1 }],
                (values) => {
                    frappe.call({
                        method: "paideia_cms.api.v1.admin.trigger_translation",
                        args: { doctype: "CMS Page", name: frm.docname, language: values.language },
                        callback(r) {
                            if (r.message?.success) {
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

// ── Generation trigger ───────────────────────────────────────────────────────

function _trigger_generation(frm) {
    if (!frm.doc.source_file) {
        frappe.msgprint({ title: "No Source File", message: "Attach a PDF, DOCX, XLSX, or TXT file and save first.", indicator: "orange" });
        return;
    }
    if (!frm.doc.template) {
        frappe.msgprint({ title: "No Template", message: "Select a template first.", indicator: "orange" });
        return;
    }

    const msg = frm.doc.content_json
        ? "Re-run AI generation? Existing content will be overwritten."
        : "Start AI generation from the uploaded document?";

    frappe.confirm(msg, () => {
        frappe.call({
            method: "paideia_cms.api.v1.admin.trigger_generation",
            args: { doctype: "CMS Page", name: frm.docname },
            freeze: true,
            freeze_message: "Queuing AI generation…",
            callback(r) {
                if (r.message?.success) {
                    frm.doc.generation_status = "Queued";
                    _render_generation_banner(frm);
                    _set_primary_action(frm);
                    _start_polling(frm);
                }
            },
        });
    });
}

// ── Image slots upload UI ─────────────────────────────────────────────────────

async function _render_image_slots(frm) {
    const $wrapper = $(frm.fields_dict.image_slots_html.$wrapper);
    $wrapper.empty();
    if (!frm.doc.template) return;

    const r = await frappe.db.get_value("CMS Template", frm.doc.template, "image_slots");
    const raw = r.message?.image_slots;
    if (!raw) return;

    let slots;
    try { slots = JSON.parse(raw); } catch { return; }
    if (!slots?.length) return;

    const overrides = JSON.parse(frm.doc.image_overrides || "{}");
    const $grid = $('<div class="row g-3 mt-1"></div>').appendTo($wrapper);

    slots.forEach(slot => {
        const url = overrides[slot.key] || "";
        const $col = $('<div class="col-sm-4"></div>').appendTo($grid);
        $col.html(`
            <div class="border rounded p-2">
                <div class="small fw-semibold mb-1">${slot.label}</div>
                ${slot.description ? `<div class="small text-muted mb-2">${slot.description}</div>` : ""}
                ${url ? `<img src="${url}" class="img-fluid rounded mb-2" style="max-height:72px;object-fit:cover;width:100%">` : ""}
                <button class="btn btn-xs btn-default w-100 btn-slot-upload"
                    data-key="${slot.key}" data-label="${slot.label}">
                    ${url ? "↑ Replace" : "↑ Upload"}
                </button>
                ${url ? `<button class="btn btn-xs btn-danger w-100 mt-1 btn-slot-remove" data-key="${slot.key}">Remove</button>` : ""}
            </div>`);
    });

    $wrapper.on("click", ".btn-slot-upload", function () {
        const key = $(this).data("key");
        const label = $(this).data("label");
        frappe.prompt(
            [{ fieldname: "image", fieldtype: "Attach Image", label, reqd: 1 }],
            async ({ image }) => {
                const current = JSON.parse(frm.doc.image_overrides || "{}");
                current[key] = image;
                await frm.set_value("image_overrides", JSON.stringify(current, null, 2));
                frm.save().then(() => _render_image_slots(frm));
            },
            `Upload: ${label}`, "Upload"
        );
    });

    $wrapper.on("click", ".btn-slot-remove", async function () {
        const key = $(this).data("key");
        const current = JSON.parse(frm.doc.image_overrides || "{}");
        delete current[key];
        await frm.set_value("image_overrides", JSON.stringify(current, null, 2));
        frm.save().then(() => _render_image_slots(frm));
    });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function _publish(frm) {
    frappe.confirm("Publish this page? It will be visible on the frontend immediately.", () => {
        _set_workflow_state(frm, "Published");
    });
}

function _set_workflow_state(frm, state) {
    frappe.call({
        method: "frappe.client.set_value",
        args: { doctype: "CMS Page", name: frm.docname, fieldname: "workflow_state", value: state },
        callback(r) {
            if (!r.exc) {
                frm.reload_doc();
                frappe.show_alert({ message: state === "Published" ? "Page published." : "Page unpublished.", indicator: state === "Published" ? "green" : "orange" });
            }
        },
    });
}

function _is_generating(frm) {
    return _is_generating_status(frm.doc?.generation_status);
}

function _is_generating_status(status) {
    // Also matches agent step messages like "Generating — agent job abc123"
    return ["Queued", "Extracting", "Generating"].includes(status)
        || (!!status && status.startsWith("Generating"));
}

function _set_status_colour(frm) {
    const map = {
        "Queued":     "orange",
        "Extracting": "blue",
        "Generating": "blue",
        "Completed":  "green",
        "Failed":     "red",
    };
    frm.set_indicator_formatter("generation_status",
        () => map[frm.doc?.generation_status] || "gray");
}
