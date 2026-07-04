# Re-export everything from the real hooks module so Frappe can read app metadata
# when it loads the app under the old "pdcms_app" name.
from paideia_cms.hooks import *  # noqa: F401, F403
