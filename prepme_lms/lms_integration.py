"""
LMS integration for prepme_lms - via DATA records only.

The stock LMS app cannot be extended by editing its files (and on managed hosts
like Frappe Cloud the app directory is read-only). But the LMS sidebar's "More"
menu is populated from `LMS Sidebar Item` child rows on `LMS Settings`, each
linking a `Web Page` - all site-database records, which ARE writable on Frappe
Cloud. So prepme_lms adds its "Calendar" entry there as data, applied on
install/migrate. Nothing in the LMS app is modified.

The link points at the prepme_lms Study Hub SPA (/prepme/calendar). A Web Page
routed at "prepme/calendar" does not shadow that route - the website route rule
for /prepme wins - it only supplies the route string to the sidebar item.
"""

import frappe

CALENDAR_ROUTE = "prepme/calendar"
CALENDAR_TITLE = "Calendar"
CALENDAR_ICON = "Calendar"


def setup_calendar_link():
	"""Add the Calendar entry to the LMS sidebar 'More' menu (idempotent)."""
	if not frappe.db.exists("DocType", "LMS Sidebar Item"):
		return  # LMS not installed / incompatible version

	web_page = _ensure_web_page()
	_ensure_sidebar_item(web_page)
	frappe.db.commit()


def remove_calendar_link():
	"""Remove the Calendar entry from the LMS sidebar (on uninstall)."""
	if frappe.db.exists("DocType", "LMS Sidebar Item"):
		try:
			settings = frappe.get_single("LMS Settings")
			settings.sidebar_items = [
				row for row in settings.sidebar_items if row.route != CALENDAR_ROUTE
			]
			settings.save(ignore_permissions=True)
		except Exception:
			pass

	if frappe.db.exists("Web Page", {"route": CALENDAR_ROUTE}):
		frappe.delete_doc(
			"Web Page",
			frappe.db.get_value("Web Page", {"route": CALENDAR_ROUTE}, "name"),
			force=True,
			ignore_permissions=True,
		)
	frappe.db.commit()


def _ensure_web_page() -> str:
	"""A published Web Page that supplies the route; its content is never shown."""
	existing = frappe.db.get_value("Web Page", {"route": CALENDAR_ROUTE}, "name")
	if existing:
		return existing

	doc = frappe.new_doc("Web Page")
	doc.title = CALENDAR_TITLE
	doc.route = CALENDAR_ROUTE
	doc.published = 1
	doc.main_section = (
		'<div style="padding:2rem;text-align:center">'
		'Opening the calendar… '
		'<a href="/prepme/calendar">Continue</a></div>'
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_sidebar_item(web_page: str):
	settings = frappe.get_single("LMS Settings")

	for row in settings.sidebar_items:
		if row.web_page == web_page or row.route == CALENDAR_ROUTE:
			return  # already present

	settings.append("sidebar_items", {"web_page": web_page, "icon": CALENDAR_ICON})
	settings.save(ignore_permissions=True)
