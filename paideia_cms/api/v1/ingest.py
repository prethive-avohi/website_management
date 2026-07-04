import json
import frappe
from paideia_cms.api.response import success, error
from paideia_cms.utils.slugify import slugify

_VALID_INSTITUTIONS = {"", "uws", "presidency"}
_VALID_STUDY_LEVELS = {
    "Undergraduate", "Postgraduate", "Professional",
    "Short Course", "Certificate",
}


@frappe.whitelist()
def ingest_course(
    title,
    institution,
    study_level,
    slug=None,
    content_json=None,
    template=None,
    seo_title=None,
    seo_description=None,
    publish=False,
):
    """
    Create or update a CMS Course from an external system.

    Requires Frappe API key authentication:
        Authorization: token <api_key>:<api_secret>

    POST /api/method/paideia_cms.api.v1.ingest.ingest_course

    Payload:
        title           str  required
        institution     str  required  — 'uws' | 'presidency'
        study_level     str  required  — 'Undergraduate' | 'Postgraduate' | ...
        slug            str  optional  — auto-generated from title if omitted
        content_json    obj  optional  — pre-built content dict; leave empty to fill via AI later
        template        str  optional  — CMS Template name (e.g. 'TMPL-0001')
        seo_title       str  optional
        seo_description str  optional
        publish         bool optional  — True → workflow_state=Published → deploy hook fires

    Behaviour:
        - If a course with the resolved slug already exists → UPDATE it (upsert).
        - If not → CREATE a new CMS Course.
        - If publish=True and workflow_state transitions to Published →
          on_update() fires the debounced Vercel deploy hook automatically.
        - Translation records already link to the course by name (primary key) —
          no extra wiring needed.
    """
    # ── Validate ──────────────────────────────────────────────────────────────
    if not title:
        return error("title is required")

    if institution not in _VALID_INSTITUTIONS:
        return error(
            f"institution must be one of: {', '.join(sorted(_VALID_INSTITUTIONS) or ['(empty)'])}"
        )

    if study_level not in _VALID_STUDY_LEVELS:
        return error(
            f"study_level must be one of: {', '.join(sorted(_VALID_STUDY_LEVELS))}"
        )

    # ── Normalise content_json ─────────────────────────────────────────────
    if content_json is not None:
        if isinstance(content_json, (dict, list)):
            content_json_str = json.dumps(content_json)
        else:
            try:
                json.loads(content_json)          # validate if string was passed
                content_json_str = content_json
            except (json.JSONDecodeError, TypeError):
                return error("content_json must be a valid JSON object")
    else:
        content_json_str = None

    publish = frappe.utils.cint(publish) == 1 or publish is True

    # ── Resolve slug ──────────────────────────────────────────────────────────
    resolved_slug = slug.strip() if slug else slugify(title)

    # ── Upsert ────────────────────────────────────────────────────────────────
    existing_name = frappe.db.get_value("CMS Course", {"slug": resolved_slug}, "name")

    if existing_name:
        doc = frappe.get_doc("CMS Course", existing_name)
        doc.title        = title
        doc.institution  = institution
        doc.study_level  = study_level
        if content_json_str is not None:
            doc.content_json = content_json_str
        if template:
            doc.template = template
        if seo_title is not None:
            doc.seo_title = seo_title
        if seo_description is not None:
            doc.seo_description = seo_description
        if publish:
            doc.workflow_state = "Published"
        doc.save(ignore_permissions=True)
        action = "updated"
    else:
        doc = frappe.get_doc({
            "doctype":      "CMS Course",
            "title":        title,
            "slug":         resolved_slug,
            "institution":  institution,
            "study_level":  study_level,
            "content_json": content_json_str,
            "template":     template,
            "seo_title":    seo_title,
            "seo_description": seo_description,
            "workflow_state": "Published" if publish else "Draft",
        })
        doc.insert(ignore_permissions=True)
        action = "created"

    frappe.db.commit()

    url = f"/en/{doc.institution}/{doc.study_level.lower().replace(' ', '-')}/{doc.slug}" \
          if doc.institution else f"/en/{doc.slug}"

    return success({
        "name":      doc.name,
        "slug":      doc.slug,
        "action":    action,
        "published": doc.workflow_state == "Published",
        "url":       url,
    })


@frappe.whitelist()
def ingest_blog(
    title,
    slug=None,
    content_json=None,
    template=None,
    seo_title=None,
    seo_description=None,
    publish=False,
):
    """
    Create or update a CMS Blog from an external system.

    Same pattern as ingest_course — upsert by slug, optional publish.

    POST /api/method/paideia_cms.api.v1.ingest.ingest_blog
    """
    if not title:
        return error("title is required")

    if content_json is not None:
        if isinstance(content_json, (dict, list)):
            content_json_str = json.dumps(content_json)
        else:
            try:
                json.loads(content_json)
                content_json_str = content_json
            except (json.JSONDecodeError, TypeError):
                return error("content_json must be a valid JSON object")
    else:
        content_json_str = None

    publish = frappe.utils.cint(publish) == 1 or publish is True
    resolved_slug = slug.strip() if slug else slugify(title)

    existing_name = frappe.db.get_value("CMS Blog", {"slug": resolved_slug}, "name")

    if existing_name:
        doc = frappe.get_doc("CMS Blog", existing_name)
        doc.title        = title
        if content_json_str is not None:
            doc.content_json = content_json_str
        if template:
            doc.template = template
        if seo_title is not None:
            doc.seo_title = seo_title
        if seo_description is not None:
            doc.seo_description = seo_description
        if publish:
            doc.workflow_state = "Published"
        doc.save(ignore_permissions=True)
        action = "updated"
    else:
        doc = frappe.get_doc({
            "doctype":         "CMS Blog",
            "title":           title,
            "slug":            resolved_slug,
            "content_json":    content_json_str,
            "template":        template,
            "seo_title":       seo_title,
            "seo_description": seo_description,
            "workflow_state":  "Published" if publish else "Draft",
        })
        doc.insert(ignore_permissions=True)
        action = "created"

    frappe.db.commit()

    return success({
        "name":      doc.name,
        "slug":      doc.slug,
        "action":    action,
        "published": doc.workflow_state == "Published",
        "url":       f"/en/blog/{doc.slug}",
    })
