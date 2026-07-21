"""
Course aggregation service.

Assembles the full course tree - course meta, instructors, chapters, lessons,
and every video/document referenced by those lessons - into a single payload.

Two details of the upstream LMS schema drive this implementation:

1. Ordering is NOT stored on `Course Chapter` / `Course Lesson`. It lives on the
   child rows: `LMS Course.chapters` (Chapter Reference) and
   `Course Chapter.lessons` (Lesson Reference). We therefore walk the parent's
   child table rather than sorting the chapter/lesson records themselves.

2. Lesson media is embedded in the lesson body (EditorJS blocks or legacy
   Markdown macros), not in dedicated fields. `content_parser` extracts it.
"""

import frappe
from frappe import _
from frappe.utils import get_url

from prepme_lms.services.course.content_parser import build_video, parse_lesson_content

COURSE_FIELDS = [
	"name", "title", "description", "short_introduction", "image", "video_link",
	"tags", "category", "status", "published", "published_on", "featured",
	"upcoming", "disable_self_learning", "enable_certification", "paid_certificate",
	"evaluator", "paid_course", "course_price", "amount_usd", "currency",
	"enrollments", "lessons", "rating", "card_gradient", "timezone",
	"owner", "creation", "modified",
]

CHAPTER_FIELDS = [
	"name", "title", "course", "course_title",
	"is_scorm_package", "scorm_package", "scorm_package_path",
	"manifest_file", "launch_file",
]

LESSON_FIELDS = [
	"name", "title", "chapter", "course", "body", "content",
	"include_in_preview", "youtube", "quiz_id", "question", "file_type",
	"is_scorm_package", "instructor_notes", "instructor_content",
	"idx", "docstatus", "owner", "modified_by", "creation", "modified",
]


class CourseNotFound(Exception):
	pass


class CourseAccessDenied(Exception):
	pass


def get_course_details(
	course: str,
	include_content: bool = True,
	include_instructor_notes: bool = False,
) -> dict:
	"""Build the complete course payload.

	Args:
		course: `LMS Course` name (slug) or exact course title.
		include_content: include raw lesson blocks/body alongside the
			extracted media. Set False for a lighter curriculum-only response.
		include_instructor_notes: include instructor-only notes. Honoured only
			for instructors and moderators.

	Raises:
		CourseNotFound: no such course.
		CourseAccessDenied: course is unpublished and the user cannot see it.
	"""
	course_name = _resolve_course(course)

	if not course_name:
		raise CourseNotFound(_("Course {0} not found").format(course))

	course_doc = frappe.get_doc("LMS Course", course_name)
	access = _get_access_context(course_doc)

	if not course_doc.published and not access["has_full_access"]:
		raise CourseAccessDenied(_("Course {0} is not published").format(course_name))

	# Instructor notes are privileged regardless of what the caller asked for.
	expose_notes = include_instructor_notes and (access["is_instructor"] or access["is_moderator"])

	chapters = _get_chapters(
		course_doc,
		access=access,
		include_content=include_content,
		include_instructor_notes=expose_notes,
	)

	return {
		"course": _serialize_course(course_doc, access),
		"chapters": chapters,
		"summary": _build_summary(chapters),
		"access": {
			"is_enrolled": access["is_enrolled"],
			"is_instructor": access["is_instructor"],
			"is_moderator": access["is_moderator"],
			"has_full_access": access["has_full_access"],
			"instructor_notes_included": expose_notes,
		},
	}


def _resolve_course(course: str) -> str | None:
	"""Look up by name (slug) first, then fall back to an exact title match."""
	course = (course or "").strip()
	if not course:
		return None

	if frappe.db.exists("LMS Course", course):
		return course

	return frappe.db.get_value("LMS Course", {"title": course}, "name")


def _get_access_context(course_doc) -> dict:
	"""Determine what this session is allowed to see."""
	user = frappe.session.user
	is_guest = user == "Guest"
	roles = set(frappe.get_roles(user)) if not is_guest else set()

	is_moderator = bool(roles & {"Moderator", "System Manager", "LMS Admin"})
	is_instructor = any(row.instructor == user for row in course_doc.instructors)

	is_enrolled = False
	if not is_guest:
		is_enrolled = bool(
			frappe.db.exists("LMS Enrollment", {"course": course_doc.name, "member": user})
		)

	return {
		"user": user,
		"is_guest": is_guest,
		"is_moderator": is_moderator,
		"is_instructor": is_instructor,
		"is_enrolled": is_enrolled,
		"has_full_access": is_moderator or is_instructor or is_enrolled,
	}


def _serialize_course(course_doc, access: dict) -> dict:
	tags = [tag.strip() for tag in (course_doc.tags or "").split(",") if tag.strip()]

	return {
		"id": course_doc.name,
		"title": course_doc.title,
		"description": course_doc.description,
		"short_introduction": course_doc.short_introduction,
		"image": _absolute(course_doc.image),
		"intro_video": _course_intro_video(course_doc.video_link),
		"tags": tags,
		"category": course_doc.category,
		"status": course_doc.status,
		"published": bool(course_doc.published),
		"published_on": course_doc.published_on,
		"featured": bool(course_doc.featured),
		"upcoming": bool(course_doc.upcoming),
		"disable_self_learning": bool(course_doc.disable_self_learning),
		"card_gradient": course_doc.card_gradient,
		"timezone": course_doc.timezone,
		"certification": {
			"enabled": bool(course_doc.enable_certification),
			"paid_certificate": bool(course_doc.paid_certificate),
			"evaluator": course_doc.evaluator,
		},
		"pricing": {
			"is_paid": bool(course_doc.paid_course),
			"amount": course_doc.course_price,
			"amount_usd": course_doc.amount_usd,
			"currency": course_doc.currency,
		},
		"stats": {
			"enrollments": course_doc.enrollments or 0,
			"lesson_count": course_doc.lessons or 0,
			"rating": course_doc.rating,
		},
		"instructors": _get_instructors(course_doc),
		"related_courses": _get_related_courses(course_doc),
		"created_on": course_doc.creation,
		"modified_on": course_doc.modified,
	}


def _course_intro_video(video_link: str) -> dict | None:
	"""The course-level promo video, stored as a bare YouTube id or a URL."""
	return build_video(video_link)


def _get_instructors(course_doc) -> list:
	usernames = [row.instructor for row in course_doc.instructors if row.instructor]

	if not usernames:
		return []

	users = frappe.get_all(
		"User",
		filters={"name": ["in", usernames]},
		fields=["name", "full_name", "first_name", "last_name", "user_image", "username"],
	)
	by_name = {user.name: user for user in users}

	instructors = []
	for username in usernames:
		user = by_name.get(username)
		if not user:
			continue
		instructors.append({
			"email": user.name,
			"username": user.username,
			"full_name": user.full_name,
			"first_name": user.first_name,
			"last_name": user.last_name,
			"user_image": _absolute(user.user_image),
		})

	return instructors


def _get_related_courses(course_doc) -> list:
	course_names = [row.course for row in course_doc.related_courses if row.course]

	if not course_names:
		return []

	related = frappe.get_all(
		"LMS Course",
		filters={"name": ["in", course_names], "published": 1},
		fields=["name", "title", "short_introduction", "image"],
	)

	return [
		{
			"id": row.name,
			"title": row.title,
			"short_introduction": row.short_introduction,
			"image": _absolute(row.image),
		}
		for row in related
	]


def _get_chapters(course_doc, access: dict, include_content: bool, include_instructor_notes: bool) -> list:
	"""Walk `Chapter Reference` rows so chapters come back in authored order."""
	chapter_names = [row.chapter for row in course_doc.chapters if row.chapter]

	if not chapter_names:
		return []

	records = frappe.get_all(
		"Course Chapter",
		filters={"name": ["in", chapter_names]},
		fields=CHAPTER_FIELDS,
	)
	by_name = {record.name: record for record in records}

	lessons_by_chapter = _get_lessons(
		chapter_names,
		access=access,
		include_content=include_content,
		include_instructor_notes=include_instructor_notes,
	)

	chapters = []
	for index, chapter_name in enumerate(chapter_names, start=1):
		record = by_name.get(chapter_name)
		if not record:
			continue

		lessons = lessons_by_chapter.get(chapter_name, [])

		chapters.append({
			"id": record.name,
			"title": record.title,
			"index": index,
			"course": record.course,
			"course_title": record.course_title,
			"lesson_count": len(lessons),
			"scorm": _serialize_scorm(record),
			"lessons": lessons,
		})

	return chapters


def _serialize_scorm(chapter) -> dict | None:
	if not chapter.is_scorm_package:
		return None

	return {
		"package": chapter.scorm_package,
		"package_path": chapter.scorm_package_path,
		"manifest_file": chapter.manifest_file,
		"launch_file": chapter.launch_file,
	}


def _get_lessons(chapter_names: list, access: dict, include_content: bool, include_instructor_notes: bool) -> dict:
	"""Fetch all lessons for the given chapters, keyed by chapter, in order.

	Lesson order lives on `Course Chapter.lessons` (Lesson Reference), so the
	reference rows are read in bulk and used to sequence each chapter's lessons.
	"""
	references = frappe.get_all(
		"Lesson Reference",
		filters={"parent": ["in", chapter_names], "parenttype": "Course Chapter"},
		fields=["parent", "lesson", "idx"],
		order_by="parent asc, idx asc",
	)

	if not references:
		return {}

	lesson_names = [row.lesson for row in references if row.lesson]
	if not lesson_names:
		return {}

	records = frappe.get_all(
		"Course Lesson",
		filters={"name": ["in", lesson_names]},
		fields=LESSON_FIELDS,
	)
	by_name = {record.name: record for record in records}

	attachments = _get_lesson_attachments(lesson_names)

	lessons_by_chapter = {}
	position = {}

	for reference in references:
		record = by_name.get(reference.lesson)
		if not record:
			continue

		chapter = reference.parent
		position[chapter] = position.get(chapter, 0) + 1

		lessons_by_chapter.setdefault(chapter, []).append(
			_serialize_lesson(
				record,
				index=position[chapter],
				access=access,
				include_content=include_content,
				include_instructor_notes=include_instructor_notes,
				attachments=attachments.get(record.name, []),
			)
		)

	return lessons_by_chapter


def _serialize_lesson(lesson, index: int, access: dict, include_content: bool, include_instructor_notes: bool, attachments: list) -> dict:
	"""Serialize one lesson, redacting the body when access is not granted."""
	is_preview = bool(lesson.include_in_preview)
	can_view_content = access["has_full_access"] or is_preview

	payload = {
		"id": lesson.name,
		"title": (lesson.title or "").strip(),
		"index": index,
		"idx": lesson.idx,
		"chapter": lesson.chapter,
		"course": lesson.course,
		"include_in_preview": is_preview,
		"is_scorm_package": bool(lesson.is_scorm_package),
		"file_type": lesson.file_type or None,
		"question": lesson.question,
		"quiz_id": lesson.quiz_id,
		"content_locked": not can_view_content,
		"docstatus": lesson.docstatus,
		"owner": lesson.owner,
		"modified_by": lesson.modified_by,
		"created_on": lesson.creation,
		"modified_on": lesson.modified,
	}

	if not can_view_content:
		# Keep the shape stable so clients can render a locked lesson row.
		payload.update({
			"content_format": None,
			"description": None,
			"content_text": None,
			"videos": [],
			"documents": [],
			"images": [],
			"audio": [],
			"embeds": [],
			"quizzes": [],
			"assignments": [],
			"programs": [],
			"attachments": [],
		})
		return payload

	parsed = parse_lesson_content(
		{
			"content": lesson.content,
			"body": lesson.body,
			"instructor_content": lesson.instructor_content,
			"instructor_notes": lesson.instructor_notes,
		},
		include_instructor_notes=include_instructor_notes,
	)

	# The legacy `youtube` field predates the block editor; fold it in.
	_merge_legacy_youtube(lesson.youtube, parsed["videos"])

	payload.update({
		"content_format": parsed["content_format"],
		"description": parsed["description"],
		"content_text": parsed["content_text"],
		"videos": parsed["videos"],
		"documents": parsed["documents"],
		"images": parsed["images"],
		"audio": parsed["audio"],
		"embeds": parsed["embeds"],
		"quizzes": parsed["quizzes"],
		"assignments": parsed["assignments"],
		"programs": parsed["programs"],
		"attachments": attachments,
	})

	if include_content:
		payload["content"] = parsed["blocks"]
		payload["body"] = lesson.body

	if include_instructor_notes:
		payload["instructor_notes"] = lesson.instructor_notes
		payload["instructor_content"] = lesson.instructor_content

	return payload


def _merge_legacy_youtube(youtube: str, videos: list) -> None:
	"""Add the lesson's standalone `youtube` field unless already present."""
	video = build_video(youtube, service="youtube")
	if not video:
		return

	if any(existing.get("video_id") == video["video_id"] for existing in videos):
		return

	video.update({"caption": None, "source": "youtube_field"})
	videos.append(video)


def _get_lesson_attachments(lesson_names: list) -> dict:
	"""Files attached to the lesson records themselves, keyed by lesson."""
	files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Course Lesson",
			"attached_to_name": ["in", lesson_names],
		},
		fields=[
			"name", "file_name", "file_url", "file_size",
			"is_private", "attached_to_name", "creation",
		],
	)

	attachments = {}
	for file in files:
		attachments.setdefault(file.attached_to_name, []).append({
			"file_id": file.name,
			"file_name": file.file_name,
			"file_url": file.file_url,
			"url": _absolute(file.file_url),
			"file_size": file.file_size,
			"is_private": bool(file.is_private),
			"uploaded_on": file.creation,
			"source": "lesson_attachment",
		})

	return attachments


def _build_summary(chapters: list) -> dict:
	lessons = [lesson for chapter in chapters for lesson in chapter["lessons"]]

	return {
		"total_chapters": len(chapters),
		"total_lessons": len(lessons),
		"total_videos": sum(len(lesson["videos"]) for lesson in lessons),
		"total_documents": sum(
			len(lesson["documents"]) + len(lesson["attachments"]) for lesson in lessons
		),
		"total_quizzes": sum(len(lesson["quizzes"]) for lesson in lessons),
		"total_assignments": sum(len(lesson["assignments"]) for lesson in lessons),
		"locked_lessons": sum(1 for lesson in lessons if lesson["content_locked"]),
	}


def _absolute(file_url: str) -> str | None:
	if not file_url:
		return None
	if str(file_url).startswith(("http://", "https://", "data:")):
		return file_url
	return get_url(file_url)
