# Compatibility shim — the Frappe Cloud site has this app registered as "pdcms_app"
# but the Python package was renamed to "paideia_cms". This empty package satisfies
# Frappe's import of pdcms_app during migration. All real code is in paideia_cms/.
