"""
Calendar API - v1.

Endpoint:
	GET|POST /api/method/prepme_lms.api.v1.calendar.get_my_classes

Returns the logged-in user's scheduled live classes, already shaped for the
frappe-ui Calendar component.

Consumer note: this endpoint is called by frappe-ui's `createResource`, which
unwraps `response.message` into `resource.data`. It therefore *returns* the
payload directly (so it lands in `message`) rather than using the
success/data envelope the course API uses for external callers. On failure it
raises, which frappe-ui surfaces as `resource.error`.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from prepme_lms.services.calendar.calendar_service import get_my_classes as build_my_classes


# POST is allowed because frappe-ui's createResource posts to /api/method/*.
# No allow_guest: Frappe rejects unauthenticated callers with a 403, which is
# the behaviour we want for a personal schedule.
@frappe.whitelist(methods=["GET", "POST"])
@rate_limit(limit=120, seconds=60)
def get_my_classes(from_date: str = None, to_date: str = None, batch: str = None):
	"""Fetch the current user's live classes as calendar events.

	Query params:
		from_date / to_date: optional YYYY-MM-DD bounds. Omit both for everything.
		batch: optional LMS Batch to restrict to. Ignored if the user has no
			access to that batch.

	Returns a dict {events, summary, context}. Each event carries the keys
	frappe-ui's Calendar reads (id, title, participant, venue, fromDate, toDate,
	fromTime, toTime, color) plus detail fields - description, join_url,
	host_name, batch_title, duration, timezone.
	"""
	try:
		return build_my_classes(from_date=from_date, to_date=to_date, batch=batch)
	except Exception:
		frappe.log_error(
			title="prepme_lms: get_my_classes failed",
			message=f"user={frappe.session.user} from={from_date} to={to_date}\n\n{frappe.get_traceback()}",
		)
		frappe.throw(_("Unable to fetch your schedule"))
