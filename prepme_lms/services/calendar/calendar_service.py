"""
Class schedule service.

Builds the logged-in user's live-class schedule in the exact event shape the
frappe-ui Calendar component expects:

	{id, title, participant, venue, fromDate, toDate, fromTime, toTime, color}

A user sees a live class when any of the following holds:

	* they are enrolled in the class's batch  (LMS Batch Enrollment)
	* they are an instructor on that batch    (LMS Batch.instructors)
	* they are the host of the class          (LMS Live Class.host)

`LMS Live Class` stores a start `time` and an integer `duration` in minutes;
there is no end-time column, so the end is derived. Classes are coloured per
batch so every session of the same batch reads as one series.
"""

import hashlib
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import getdate

# The colours frappe-ui's Calendar understands (calendarUtils.js colorMap).
EVENT_COLORS = ["blue", "green", "violet", "amber", "cyan", "orange", "pink"]

LIVE_CLASS_FIELDS = [
	"name", "title", "description", "date", "time", "duration", "timezone",
	"host", "batch_name", "join_url", "start_url", "meeting_id",
	"auto_recording", "attendees", "owner", "creation", "modified",
]


def get_my_classes(from_date=None, to_date=None, batch=None) -> dict:
	"""Return the current user's scheduled live classes as calendar events.

	Args:
		from_date / to_date: optional YYYY-MM-DD bounds. Omit both to get
			every class the user can see.
		batch: optional LMS Batch name to restrict the result to.
	"""
	user = frappe.session.user

	if user == "Guest":
		return _empty_result(user)

	# Moderators/admins see every scheduled class on the site (an admin overview),
	# not just batches they personally belong to.
	is_moderator = _is_moderator(user)
	batches = _get_user_batches(user)

	classes = _get_live_classes(user, batches, from_date, to_date, batch, is_moderator)

	if not classes:
		return _empty_result(user, batches)

	batch_titles = _get_batch_titles({row.batch_name for row in classes if row.batch_name})
	host_names = _get_user_names({row.host for row in classes if row.host})

	events = [
		_serialize_event(row, batch_titles, host_names)
		for row in classes
	]
	events.sort(key=lambda e: (e["fromDate"], e["fromTime"] or ""))

	# Batches actually represented in the result (covers the moderator-sees-all
	# case, where the classes span batches the user isn't a member of).
	result_batches = {row.batch_name for row in classes if row.batch_name}

	return {
		"events": events,
		"summary": _build_summary(events, result_batches),
		"context": {
			"user": user,
			"is_moderator": is_moderator,
			"batches": [
				{"id": name, "title": batch_titles.get(name, name)}
				for name in sorted(result_batches)
			],
			"from_date": from_date,
			"to_date": to_date,
		},
	}


def _empty_result(user, batches=None) -> dict:
	return {
		"events": [],
		"summary": {"total_events": 0, "total_batches": len(batches or []), "upcoming": 0, "past": 0},
		"context": {"user": user, "batches": [], "from_date": None, "to_date": None},
	}


def _is_moderator(user: str) -> bool:
	roles = set(frappe.get_roles(user))
	return bool(roles & {"Moderator", "System Manager", "LMS Admin", "Course Creator"})


def _get_user_batches(user: str) -> set:
	"""Batches the user is enrolled in or teaches."""
	enrolled = frappe.get_all(
		"LMS Batch Enrollment",
		filters={"member": user},
		pluck="batch",
	)

	teaching = frappe.get_all(
		"Course Instructor",
		filters={"instructor": user, "parenttype": "LMS Batch"},
		pluck="parent",
	)

	return {b for b in list(enrolled) + list(teaching) if b}


def _get_live_classes(user, batches, from_date, to_date, batch, is_moderator=False) -> list:
	"""Fetch live classes visible to this user, optionally date/batch bounded."""
	date_filters = {}
	if from_date:
		date_filters["date"] = [">=", getdate(from_date)]
	if to_date:
		# a second condition on the same field needs the "between" form
		if from_date:
			date_filters["date"] = ["between", [getdate(from_date), getdate(to_date)]]
		else:
			date_filters["date"] = ["<=", getdate(to_date)]

	# Moderators see all classes; a specific batch just narrows the result.
	if is_moderator:
		filters = dict(date_filters)
		if batch:
			filters["batch_name"] = batch
		return frappe.get_all("LMS Live Class", filters=filters, fields=LIVE_CLASS_FIELDS)

	if batch:
		# An explicit batch is honoured only if the user may see it.
		if batch not in batches:
			return []
		visible_batches = {batch}
	else:
		visible_batches = batches

	rows = {}

	if visible_batches:
		filters = dict(date_filters)
		filters["batch_name"] = ["in", list(visible_batches)]
		for row in frappe.get_all("LMS Live Class", filters=filters, fields=LIVE_CLASS_FIELDS):
			rows[row.name] = row

	# Classes the user hosts, even for a batch they are not enrolled in.
	if not batch:
		filters = dict(date_filters)
		filters["host"] = user
		for row in frappe.get_all("LMS Live Class", filters=filters, fields=LIVE_CLASS_FIELDS):
			rows.setdefault(row.name, row)

	return list(rows.values())


def _serialize_event(row, batch_titles: dict, host_names: dict) -> dict:
	"""Map one LMS Live Class onto a frappe-ui Calendar event."""
	start_time = _format_time(row.time)
	end_time = _add_minutes(row.time, row.duration)
	event_date = str(row.date) if row.date else None
	batch_title = batch_titles.get(row.batch_name, row.batch_name)

	return {
		# --- fields the Calendar component reads ---
		"id": row.name,
		"title": row.title or _("Live Class"),
		"participant": host_names.get(row.host, row.host),
		"venue": batch_title or _("Online"),
		"fromDate": event_date,
		"toDate": event_date,
		"fromTime": start_time,
		"toTime": end_time,
		"color": _color_for(row.batch_name or row.name),
		# --- extra detail for the event popover / custom UI ---
		"description": row.description,
		"batch": row.batch_name,
		"batch_title": batch_title,
		"host": row.host,
		"host_name": host_names.get(row.host, row.host),
		"duration": row.duration,
		"timezone": row.timezone,
		"join_url": row.join_url,
		"meeting_id": row.meeting_id,
		"is_host": row.host == frappe.session.user,
		"auto_recording": row.auto_recording,
		"attendees": row.attendees,
	}


def _format_time(value) -> str | None:
	"""Frappe Time values arrive as timedelta or str; normalise to HH:MM."""
	if value is None:
		return None

	if isinstance(value, timedelta):
		total = int(value.total_seconds())
		return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"

	text = str(value)
	parts = text.split(":")
	if len(parts) >= 2:
		return f"{int(parts[0]):02d}:{int(parts[1]):02d}"

	return text


def _add_minutes(value, minutes) -> str | None:
	"""Derive the end time; LMS Live Class stores only start + duration."""
	start = _format_time(value)
	if not start:
		return None

	if not minutes:
		return start

	base = datetime.strptime(start, "%H:%M") + timedelta(minutes=int(minutes))
	return base.strftime("%H:%M")


def _color_for(key: str) -> str:
	"""Stable colour per batch, so one batch reads as a single series.

	Uses a digest rather than sum(ord(...)), which collides readily on similar
	names, or the builtin hash(), which is salted per process and would change
	the colours on every restart.
	"""
	if not key:
		return EVENT_COLORS[0]

	digest = hashlib.md5(str(key).encode("utf-8")).hexdigest()
	return EVENT_COLORS[int(digest, 16) % len(EVENT_COLORS)]


def _get_batch_titles(batch_names: set) -> dict:
	if not batch_names:
		return {}

	rows = frappe.get_all(
		"LMS Batch",
		filters={"name": ["in", list(batch_names)]},
		fields=["name", "title"],
	)
	return {row.name: row.title for row in rows}


def _get_user_names(users: set) -> dict:
	if not users:
		return {}

	rows = frappe.get_all(
		"User",
		filters={"name": ["in", list(users)]},
		fields=["name", "full_name"],
	)
	return {row.name: row.full_name or row.name for row in rows}


def _build_summary(events: list, batches: set) -> dict:
	today = str(getdate())
	upcoming = sum(1 for e in events if e["fromDate"] and e["fromDate"] >= today)

	return {
		"total_events": len(events),
		"total_batches": len(batches),
		"upcoming": upcoming,
		"past": len(events) - upcoming,
	}
