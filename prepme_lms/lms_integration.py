"""
LMS integration for prepme_lms - via DATA records only.

The stock LMS app cannot be extended by editing its files (and on managed hosts
like Frappe Cloud the app directory is read-only). But the LMS sidebar's "More"
menu is populated from `LMS Sidebar Item` child rows on `LMS Settings`, each
linking a `Web Page` - all site-database records, which ARE writable on Frappe
Cloud. So prepme_lms adds its entries there as data, applied on install/migrate.
Nothing in the LMS app is modified.

Each entry points at the prepme_lms Study Hub SPA. A Web Page routed at
"prepme/..." does not shadow that route - the website route rule for /prepme
wins - it only supplies the route string to the sidebar item.
"""

import frappe

# (route, title shown in the menu, lucide icon name)
SIDEBAR_LINKS = [
	("prepme/courses", "Courses", "BookOpen"),
	("prepme/calendar", "Calendar", "Calendar"),
]


def setup_sidebar_links():
	"""Add prepme_lms entries to the LMS sidebar 'More' menu (idempotent)."""
	if not frappe.db.exists("DocType", "LMS Sidebar Item"):
		return  # LMS not installed / incompatible version

	settings = frappe.get_single("LMS Settings")
	existing_routes = {row.route for row in settings.sidebar_items}
	changed = False

	for route, title, icon in SIDEBAR_LINKS:
		web_page = _ensure_web_page(route, title)
		if route not in existing_routes and not any(
			row.web_page == web_page for row in settings.sidebar_items
		):
			settings.append("sidebar_items", {"web_page": web_page, "icon": icon})
			changed = True

	if changed:
		settings.save(ignore_permissions=True)
	frappe.db.commit()


def remove_sidebar_links():
	"""Remove prepme_lms entries from the LMS sidebar (on uninstall)."""
	routes = {route for route, _, _ in SIDEBAR_LINKS}

	if frappe.db.exists("DocType", "LMS Sidebar Item"):
		try:
			settings = frappe.get_single("LMS Settings")
			settings.sidebar_items = [
				row for row in settings.sidebar_items if row.route not in routes
			]
			settings.save(ignore_permissions=True)
		except Exception:
			pass

	for route in routes:
		name = frappe.db.get_value("Web Page", {"route": route}, "name")
		if name:
			frappe.delete_doc("Web Page", name, force=True, ignore_permissions=True)

	frappe.db.commit()


def _ensure_web_page(route: str, title: str) -> str:
	"""A published Web Page that supplies the route; its content is never shown."""
	existing = frappe.db.get_value("Web Page", {"route": route}, "name")
	if existing:
		return existing

	doc = frappe.new_doc("Web Page")
	doc.title = title
	doc.route = route
	doc.published = 1
	doc.main_section = (
		f'<div style="padding:2rem;text-align:center">Opening {title}… '
		f'<a href="/{route}">Continue</a></div>'
	)
	doc.insert(ignore_permissions=True)
	return doc.name


# Backwards-compatible aliases (hooks may still reference the old names).
setup_calendar_link = setup_sidebar_links
remove_calendar_link = remove_sidebar_links
