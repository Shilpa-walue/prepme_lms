import frappe

no_cache = 1


def get_context(context):
	"""Boot data for the Study Hub SPA (served at /prepme)."""
	context.boot = frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"read_only_mode": frappe.flags.read_only,
			"csrf_token": frappe.sessions.get_csrf_token(),
		}
	)
	context.title = "Study Hub"
	context.favicon = (
		frappe.db.get_single_value("Website Settings", "favicon")
		or "/assets/prepme_lms/frontend/favicon.png"
	)
	frappe.db.commit()
	return context
