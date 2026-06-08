frappe.ui.form.on("CMS Course", {
    refresh(frm) {
        if (frm.is_new()) return;

        _render_generation_banner(frm);
        _set_primary_action(frm);
        _add_menu_buttons(frm);

        if (_is_generating_status(frm.doc?.generation_status)) {
            _start_polling(frm);
        }
    },

    onload(frm) {
        if (!frm.is_new() && _is_generating_status(frm.doc?.generation_status)) {
            _start_polling(frm);
        }
    },
});

function _set_primary_action(frm) {
    frm.page.clear_primary_action();

    if (frm.doc.content_json) {
        frm.page.set_primary_action(__("Preview"), () => {
            const url = `/api/method/pdcms_app.api.v1.preview.render_course?name=${encodeURIComponent(frm.docname)}`;
            window.open(url, "_blank");
        }, "eye");
    } else if (frm.doc.source_file && !_is_generating_status(frm.doc?.generation_status)) {
        frm.page.set_primary_action(__("Generate Content"), () => {
            _trigger_generation(frm);
        }, "play");
    }
}

function _render_generation_banner(frm) {
    frm.dashboard.clear_headline();
    const status = frm.doc?.generation_status;
    const banners = {
        "Queued":     ["yellow", `<div class="d-flex align-items-center gap-2"><div class="spinner-border spinner-border-sm text-primary" role="status"></div><span><b>AI is generating content…</b> Status: <b>${status}</b> — This page will refresh automatically.</span></div>`],
        "Extracting": ["yellow", `<div class="d-flex align-items-center gap-2"><div class="spinner-border spinner-border-sm text-primary" role="status"></div><span><b>AI is generating content…</b> Status: <b>${status}</b> — This page will refresh automatically.</span></div>`],
        "Generating": ["yellow", `<div class="d-flex align-items-center gap-2"><div class="spinner-border spinner-border-sm text-primary" role="status"></div><span><b>AI is generating content…</b> Status: <b>${status}</b> — This page will refresh automatically.</span></div>`],
        "Completed":  ["green", `<span>✓ <b>Content generated.</b> Review the Content JSON below then click <b>Preview</b>.</span>`],
        "Failed":     ["red",   `<span>✗ <b>Generation failed.</b> See AI Error Log. Click <b>AI → Generate Content</b> to retry.</span>`],
    };
    const banner = banners[status];
    if (banner) {
        frm.dashboard.set_headline_alert(banner[1], banner[0]);
    }
}

function _start_polling(frm) {
    if (frm._cms_poll_timer) return;

    frm._cms_poll_timer = setInterval(() => {
        frappe.db.get_value("CMS Course", frm.docname, "generation_status")
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

function _add_menu_buttons(frm) {
    if (frm.doc.content_json) {
        frm.add_custom_button(__("Preview"), () => {
            const url = `/api/method/pdcms_app.api.v1.preview.render_course?name=${encodeURIComponent(frm.docname)}`;
            window.open(url, "_blank");
        }, __("View"));
    }

    frm.add_custom_button(__("Generate Content"), () => {
        _trigger_generation(frm);
    }, __("AI"));
}

function _trigger_generation(frm) {
    if (!frm.doc.source_file) {
        frappe.msgprint({ title: "No Source File", message: "Attach a PDF or DOCX file and save first.", indicator: "orange" });
        return;
    }

    const msg = frm.doc.content_json
        ? "Re-run AI generation? Existing content will be overwritten."
        : "Start AI generation from the uploaded document?";

    frappe.confirm(msg, () => {
        frappe.call({
            method: "pdcms_app.api.v1.admin.trigger_generation",
            args: { doctype: "CMS Course", name: frm.docname },
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

function _is_generating_status(status) {
    return ["Queued", "Extracting", "Generating"].includes(status);
}
