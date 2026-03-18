app_name = "paideia_cms"
app_title = "Paideia CMS"
app_publisher = "Paideia"
app_description = "Custom CMS for Paideia website"
app_email = "info@paideia.com"
app_license = "MIT"

# DocType JS — path relative to the app package (paideia_cms/)
doctype_js = {
    "Paideia Content Generator": "paideia_cms/doctype/paideia_content_generator/paideia_content_generator.js",
    "Paideia Bulk Content Generator": "paideia_cms/doctype/paideia_bulk_content_generator/paideia_bulk_content_generator.js"
}

# Installing
after_install = "paideia_cms.install.after_install"
