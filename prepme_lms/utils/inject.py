"""
Inject the Study Tutor loader into the stock Frappe LMS pages.

This is an `after_request` hook: it rewrites the HTML response bytes in memory
before they leave the server. That works regardless of which template the LMS
uses (its SPA shell honours no include hooks) and on managed hosts like Frappe
Cloud, where the app files are read-only — nothing is written to disk.

The loader is a prepme_lms asset (/assets/prepme_lms/js/study_tutor_loader.js),
served same-origin. The vendor widget URL comes from site config
(`study_tutor_widget_url`) and is passed through as a data attribute, so it can
be changed (e.g. http → https) without a rebuild. When it is unset, nothing is
injected.
"""

import frappe

LOADER_SRC = "/assets/prepme_lms/js/study_tutor_loader.js"
COURSE_PATH = "/lms/courses/"


def inject_study_tutor_script(response, **kwargs):
	"""Splice the Study Tutor loader before </body> on LMS pages."""
	try:
		request = getattr(frappe.local, "request", None)
		if not request:
			return

		# The LMS SPA lives under /lms. Inject on those pages only; the loader
		# itself shows the widget only on course/lesson pages and re-scopes on
		# SPA navigation (so it works no matter which /lms page loaded first).
		path = getattr(request, "path", "") or ""
		if path != "/lms" and not path.startswith("/lms/"):
			return

		content_type = response.headers.get("Content-Type", "")
		if "text/html" not in content_type:
			return

		widget_url = frappe.conf.get("study_tutor_widget_url") or ""
		if not widget_url:
			return  # not configured → nothing to inject

		html = response.get_data(as_text=True)
		if LOADER_SRC in html or "</body>" not in html:
			return

		# widget_url is admin-controlled site config; escape quotes/brackets so it
		# can't break out of the attribute.
		safe_url = (
			str(widget_url).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
		)
		snippet = (
			f'<script src="{LOADER_SRC}" '
			f'data-widget-src="{safe_url}" '
			f'data-course-path="{COURSE_PATH}" data-title="Study Tutor" defer></script>'
		)
		html = html.replace("</body>", snippet + "\n</body>", 1)
		response.set_data(html)
	except Exception:
		# Never break the page over a widget injection.
		pass
