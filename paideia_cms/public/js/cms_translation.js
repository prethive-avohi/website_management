frappe.ui.form.on("CMS Translation", {
    refresh(frm) {
        if (frm.is_new()) return;
        _set_primary_action(frm);
        _add_menu_buttons(frm);
        _render_status_banner(frm);
    },
});

function _set_primary_action(frm) {
    frm.page.clear_primary_action();

    if (frm.doc.status === "Completed" && frm.doc.workflow_state !== "Published") {
        frm.page.set_primary_action(__("Publish"), () => _publish(frm), "globe");
    }
}

function _add_menu_buttons(frm) {
    if (frm.doc.translated_json) {
        frm.add_custom_button(__("Preview"), () => {
            window.open(
                `/api/method/paideia_cms.api.v1.preview.render_translation?name=${encodeURIComponent(frm.docname)}`,
                "_blank"
            );
        }, __("View"));
    }

    if (frm.doc.workflow_state === "Published") {
        frm.add_custom_button(__("Unpublish"), () => {
            frappe.confirm("Unpublish this translation?", () => _set_workflow_state(frm, "Draft"));
        }, __("View"));
    }
}

function _render_status_banner(frm) {
    frm.dashboard.clear_headline();
    const banners = {
        "Pending":   ["yellow", "Translation not yet started."],
        "Queued":    ["yellow", "Translation queued — will start shortly."],
        "Completed": ["green",  "✓ Translation complete. Review the JSON below, then click <b>Publish</b>."],
        "Failed":    ["red",    "✗ Translation failed. Trigger again from the source document."],
    };
    const b = banners[frm.doc.status];
    if (b) frm.dashboard.set_headline_alert(b[1], b[0]);
}

function _publish(frm) {
    frappe.confirm(
        `Publish this ${frm.doc.language} translation? It will be served immediately by the API.`,
        () => _set_workflow_state(frm, "Published")
    );
}

function _set_workflow_state(frm, state) {
    frappe.call({
        method: "frappe.client.set_value",
        args: { doctype: "CMS Translation", name: frm.docname, fieldname: "workflow_state", value: state },
        callback(r) {
            if (!r.exc) {
                frm.reload_doc();
                frappe.show_alert({
                    message: state === "Published" ? "Translation published." : "Translation unpublished.",
                    indicator: state === "Published" ? "green" : "orange",
                });
            }
        },
    });
}
