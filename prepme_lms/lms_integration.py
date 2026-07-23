"""
Integration touch-points into the stock Frappe LMS app.

The LMS UI is a compiled Vue SPA that cannot be extended by another app, so the
only way to get the Study Tutor widget onto the stock LMS course pages is to add
a single <script> include to the LMS page shell (lms.html). prepme_lms owns that
include: it is (re)applied by the after_migrate / after_install hooks, so it
survives LMS updates, and removed by before_uninstall.

Everything the include points at lives in prepme_lms
(/assets/prepme_lms/js/study_tutor_loader.js), so no LMS source beyond this one
line is ever touched.
"""

import os

import frappe

MARKER = "prepme_lms:injected"
ASSET_PREFIX = "/assets/prepme_lms/js/"

SNIPPET = (
	f'\t<!-- {MARKER} (injected by prepme_lms; do not edit by hand) -->\n'
	f'\t<script src="{ASSET_PREFIX}study_tutor_loader.js" '
	f'data-course-path="/lms/courses/" data-title="Study Tutor"></script>\n'
	f'\t<script src="{ASSET_PREFIX}prepme_nav.js"></script>\n'
)


def _lms_shell_path() -> str | None:
	"""Absolute path to the LMS SPA shell, or None if LMS isn't present."""
	try:
		path = frappe.get_app_path("lms", "www", "lms.html")
	except Exception:
		return None
	return path if os.path.exists(path) else None


def inject_study_tutor():
	"""(Re)apply the prepme_lms includes to the LMS page shell.

	Self-healing: any previous prepme_lms block is stripped first, then the
	current snippet is appended, so an upgrade that changes the snippet takes
	effect on the next migrate instead of being skipped as "already present".
	"""
	path = _lms_shell_path()
	if not path:
		return

	_strip_block(path)

	with open(path, encoding="utf-8") as f:
		html = f.read()

	if "</body>" not in html:
		frappe.log_error(
			title="prepme_lms: could not inject includes",
			message=f"No </body> found in {path}",
		)
		return

	html = html.replace("</body>", SNIPPET + "</body>", 1)
	with open(path, "w", encoding="utf-8") as f:
		f.write(html)


def remove_study_tutor():
	"""Strip the prepme_lms includes from the LMS page shell (on uninstall)."""
	path = _lms_shell_path()
	if path:
		_strip_block(path)


def _strip_block(path: str):
	"""Remove any prepme_lms-injected lines from the LMS shell."""
	with open(path, encoding="utf-8") as f:
		lines = f.readlines()

	# Match any prepme_lms marker (current or older) and any injected asset.
	kept = [ln for ln in lines if "prepme_lms:" not in ln and ASSET_PREFIX not in ln]
	if len(kept) != len(lines):
		with open(path, "w", encoding="utf-8") as f:
			f.writelines(kept)
