import frappe

no_cache = 1


def get_context(context):
	"""Boot data for the Study Hub SPA (served at /prepme)."""
	context.boot = frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"read_only_mode": frappe.flags.read_only,
			"csrf_token": frappe.sessions.get_csrf_token(),
			# Study Tutor widget config. Override in site_config.json without a
			# rebuild, e.g. an https endpoint once one is available:
			#   "study_tutor_widget_url": "https://tutor.example.com/static/widget.js"
			# Empty string disables the widget.
			"study_tutor_widget_url": frappe.conf.get("study_tutor_widget_url", ""),
		}
	)
	context.title = "Study Hub"
	context.favicon = (
		frappe.db.get_single_value("Website Settings", "favicon")
		or "/assets/prepme_lms/frontend/favicon.png"
	)
	frappe.db.commit()
	return context
