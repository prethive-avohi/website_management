app_name = "paideia_cms"
app_title = "PDCMS"
app_publisher = "PDCMS"
app_description = "AI-powered multilingual headless CMS"
app_email = "dev@pdcms.io"
app_license = "MIT"
app_version = "1.0.0"

required_apps = ["frappe"]

# ---------------------------------------------------------------------------
# Install / migrate hooks
# ---------------------------------------------------------------------------
after_install = "paideia_cms.install.after_install"
after_migrate = "paideia_cms.install.after_migrate"

# ---------------------------------------------------------------------------
# DocType JS
# ---------------------------------------------------------------------------
doctype_js = {
    "CMS Template":    "public/js/cms_template.js",
    "CMS Page":        "public/js/cms_page.js",
    "CMS Blog":        "public/js/cms_blog.js",
    "CMS Course":      "public/js/cms_course.js",
    "CMS Translation": "public/js/cms_translation.js",
}

# ---------------------------------------------------------------------------
# Scheduled jobs (background worker tasks)
# ---------------------------------------------------------------------------
scheduler_events = {
    "hourly": [
        "paideia_cms.jobs.cache_cleanup.evict_expired",
    ],
    "daily": [
        "paideia_cms.jobs.ai_job_cleanup.purge_old_logs",
    ],
}

# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
has_permission = {
    "CMS Page":        "paideia_cms.cms.permissions.page_permissions.has_permission",
    "CMS Blog":        "paideia_cms.cms.permissions.page_permissions.has_permission",
    "CMS Course":      "paideia_cms.cms.permissions.page_permissions.has_permission",
    "CMS Template":    "paideia_cms.cms.permissions.page_permissions.has_permission",
}

# ---------------------------------------------------------------------------
# Override whitelisted methods (none yet)
# ---------------------------------------------------------------------------
override_whitelisted_methods = {}

# ---------------------------------------------------------------------------
# Website route rules — Frappe does NOT serve frontend pages
# (Astro is the renderer; this block left intentionally empty)
# ---------------------------------------------------------------------------
website_route_rules = []
