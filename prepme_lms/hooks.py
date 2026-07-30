app_name = "prepme_lms"
app_title = "Prepme LMS"
app_publisher = "shilpa@walue.biz"
app_description = "Learning Management System"
app_email = "shilpa@walue.biz"
app_license = "mit"

# Apps
# ------------------

# The Course API reads LMS Course / Course Chapter / Course Lesson,
# which are owned by the `lms` app. Use the "org/repo" form: a bare name makes
# the installer query GitHub to find the owning org, which fails offline or
# when the API rate-limits (403).
required_apps = ["frappe/lms"]

# Serve the Study Hub SPA (prepme_lms/frontend) under /prepme. The www page
# study_hub.html is the compiled Vue shell; vue-router handles the sub-paths.
# Everything prepme_lms adds lives on this surface - it makes no edits to the
# stock LMS app, so it is fully portable and works on managed hosts (Frappe
# Cloud) where the LMS app files are read-only.
website_route_rules = [
	{"from_route": "/prepme/<path:app_path>", "to_route": "study_hub"},
]

# Add the "Calendar" entry to the LMS sidebar "More" menu. This is done purely
# with site-database records (Web Page + LMS Sidebar Item), so it works on
# Frappe Cloud and makes no edits to the LMS app files.
after_install = "prepme_lms.lms_integration.setup_sidebar_links"
after_migrate = "prepme_lms.lms_integration.setup_sidebar_links"
before_uninstall = "prepme_lms.lms_integration.remove_sidebar_links"

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "prepme_lms",
# 		"logo": "/assets/prepme_lms/logo.png",
# 		"title": "Prepme LMS",
# 		"route": "/prepme_lms",
# 		"has_permission": "prepme_lms.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/prepme_lms/css/prepme_lms.css"
# app_include_js = "/assets/prepme_lms/js/prepme_lms.js"

# include js, css files in header of web template
# web_include_css = "/assets/prepme_lms/css/prepme_lms.css"
# web_include_js = "/assets/prepme_lms/js/prepme_lms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "prepme_lms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "prepme_lms/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "prepme_lms.utils.jinja_methods",
# 	"filters": "prepme_lms.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "prepme_lms.install.before_install"
# after_install = "prepme_lms.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "prepme_lms.uninstall.before_uninstall"
# after_uninstall = "prepme_lms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "prepme_lms.utils.before_app_install"
# after_app_install = "prepme_lms.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "prepme_lms.utils.before_app_uninstall"
# after_app_uninstall = "prepme_lms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "prepme_lms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"prepme_lms.tasks.all"
# 	],
# 	"daily": [
# 		"prepme_lms.tasks.daily"
# 	],
# 	"hourly": [
# 		"prepme_lms.tasks.hourly"
# 	],
# 	"weekly": [
# 		"prepme_lms.tasks.weekly"
# 	],
# 	"monthly": [
# 		"prepme_lms.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "prepme_lms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "prepme_lms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "prepme_lms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["prepme_lms.utils.before_request"]
# after_request = ["prepme_lms.utils.after_request"]

# Job Events
# ----------
# before_job = ["prepme_lms.utils.before_job"]
# after_job = ["prepme_lms.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"prepme_lms.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


doc_events = {
    "Student": {
        "after_insert": (
            "prepme_lms.services.google_drive.drive_service.after_student_insert"
        )
    }
}