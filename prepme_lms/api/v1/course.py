"""
Course API - v1.

Endpoints:
	GET /api/method/prepme_lms.api.v1.course.get_course_details
	GET /api/method/prepme_lms.api.v1.course.get_course_curriculum

`get_course_details` returns the complete course tree in one call: course meta,
instructors, pricing, certification, related courses, and every chapter with its
ordered lessons - including each lesson's description, YouTube/embedded videos,
documents and attachments.

`get_course_curriculum` is the lightweight variant: the same structure without
the raw lesson bodies, for rendering a syllabus or table of contents.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from prepme_lms.services.course.course_service import (
	CourseAccessDenied,
	CourseNotFound,
	get_course_details as build_course_details,
)
from prepme_lms.utils.response import error_response, success_response


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=60, seconds=60)
def get_course_details(course: str = None, include_content: int = 1, include_instructor_notes: int = 0):
	"""Fetch a course with its full chapter/lesson tree and media.

	Query params:
		course (required): LMS Course id (slug) or exact title.
		include_content: 1 (default) to include raw lesson blocks and body.
		include_instructor_notes: 1 to include instructor-only notes.
			Honoured only for that course's instructors and moderators.

	Access:
		Unpublished courses are visible only to enrolled members, the course
		instructors and moderators. For everyone else, lessons not marked
		`include_in_preview` come back with `content_locked: true` and empty
		media arrays, so the curriculum is still browsable.
	"""
	return _respond(
		course=course,
		include_content=_as_bool(include_content, default=True),
		include_instructor_notes=_as_bool(include_instructor_notes, default=False),
	)


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=60, seconds=60)
def get_course_curriculum(course: str = None):
	"""Fetch the course outline and media without the raw lesson bodies."""
	return _respond(course=course, include_content=False, include_instructor_notes=False)


def _respond(course: str, include_content: bool, include_instructor_notes: bool):
	if not course or not str(course).strip():
		error_response(_("Parameter 'course' is required"), 400, "MISSING_COURSE")
		return

	try:
		data = build_course_details(
			course=str(course).strip(),
			include_content=include_content,
			include_instructor_notes=include_instructor_notes,
		)
	except CourseNotFound as exception:
		error_response(str(exception), 404, "COURSE_NOT_FOUND")
		return
	except CourseAccessDenied as exception:
		error_response(str(exception), 403, "COURSE_ACCESS_DENIED")
		return
	except Exception:
		frappe.log_error(
			title="prepme_lms: get_course_details failed",
			message=f"course={course}\n\n{frappe.get_traceback()}",
		)
		error_response(_("Unable to fetch course details"), 500, "INTERNAL_ERROR")
		return

	success_response(_("Course details fetched successfully"), data)


def _as_bool(value, default: bool = False) -> bool:
	"""Query string values arrive as strings; normalise them."""
	if value is None or value == "":
		return default

	if isinstance(value, bool):
		return value

	return str(value).strip().lower() in ("1", "true", "yes", "y")
