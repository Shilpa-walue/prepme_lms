"""
Lesson content parser.

A `Course Lesson` stores its body in one of two formats, and both are still
in active use across older and newer courses:

1. `content` - an EditorJS document: {"blocks": [{"type": ..., "data": {...}}]}
2. `body`    - legacy Markdown carrying macros, e.g. {{ YouTubeVideo("id") }}

Media is never stored in dedicated fields, so the only way to answer
"what videos and documents does this lesson have?" is to walk the blocks
(or the macros) and classify every asset. This module does exactly that and
returns one normalised structure regardless of which format the lesson uses.

Block types produced by the LMS editor:
	embed      -> {"service": "youtube", "embed": "<url>"}
	upload     -> {"file_url": "...", "file_type": "pdf"}
	image      -> {"url": "..."} or {"file": {"url": "..."}}
	quiz       -> {"quiz": "<LMS Quiz>"}
	assignment -> {"assignment": "<LMS Assignment>"}
	program    -> {"program": "<LMS Program>"}
	paragraph / header / list / table / markdown / codeBox -> text

Legacy macro equivalents:
	{{ YouTubeVideo("id|url") }}  -> youtube video
	{{ Video("url") }}            -> uploaded video
	{{ Audio("url") }}            -> uploaded audio
	{{ PDF("url") }}              -> document
	{{ Embed("service|||url") }}  -> embedded media
	{{ Quiz("name") }}            -> quiz
	{{ Assignment("name") }}      -> assignment
	![alt](url)                   -> image
"""

import json
import re
from urllib.parse import urlparse

import frappe
from frappe.utils import get_url, strip_html_tags

MACRO_RE = re.compile(r"{{ *(\w+)\(([^{}]*)\) *}}")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(\s*([^)\s]+)")

YOUTUBE_URL_RE = re.compile(
	r"(?:youtu\.be/|youtube\.com/(?:embed/|v/|shorts/|live/|watch\?(?:[^&]*&)*v=))([A-Za-z0-9_-]{11})"
)
YOUTUBE_BARE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
VIMEO_URL_RE = re.compile(r"vimeo\.com/(?:video/)?(\d+)")

DOCUMENT_EXTENSIONS = {
	"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "csv",
	"txt", "rtf", "odt", "ods", "odp", "epub", "zip", "json",
}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg", "webp", "bmp", "ico", "avif"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "avi", "mkv", "m4v", "mpeg", "mpg"}
AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a", "aac", "flac", "opus"}

TEXT_BLOCK_TYPES = {"paragraph", "header", "markdown", "list", "quote", "table", "codeBox"}


def parse_lesson_content(lesson: dict, include_instructor_notes: bool = False) -> dict:
	"""Extract every asset referenced by a lesson.

	Returns a dict with `content_format`, the raw `blocks`, a plain-text
	`description`, and the classified `videos` / `documents` / `images` /
	`audio` / `embeds` / `quizzes` / `assignments` collections.
	"""
	collected = _new_collection()

	raw_content = lesson.get("content")
	raw_body = lesson.get("body")

	blocks = _load_blocks(raw_content)

	if blocks:
		content_format = "blocks"
		for block in blocks:
			_parse_block(block, collected, source="content")
	elif raw_body:
		content_format = "markdown"
		_parse_markdown(raw_body, collected, source="body")
	else:
		content_format = "empty"

	if include_instructor_notes:
		notes_blocks = _load_blocks(lesson.get("instructor_content"))
		if notes_blocks:
			for block in notes_blocks:
				_parse_block(block, collected, source="instructor_content")
		elif lesson.get("instructor_notes"):
			_parse_markdown(lesson["instructor_notes"], collected, source="instructor_notes")

	_enrich_with_file_metadata(collected)

	return {
		"content_format": content_format,
		"blocks": blocks,
		"description": _build_description(collected.pop("_text")),
		"videos": collected["videos"],
		"documents": collected["documents"],
		"images": collected["images"],
		"audio": collected["audio"],
		"embeds": collected["embeds"],
		"quizzes": collected["quizzes"],
		"assignments": collected["assignments"],
		"programs": collected["programs"],
	}


def build_video(value: str, service: str | None = None) -> dict | None:
	"""Normalise a standalone video reference into the same shape as a parsed one.

	Used for media stored outside the lesson body - `LMS Course.video_link` and
	the legacy `Course Lesson.youtube` field - so callers get a consistent
	structure no matter where the reference came from.
	"""
	value = (value or "").strip()
	if not value:
		return None

	service = (service or "").strip().lower() or _guess_service(value) or "youtube"
	return _normalise_embed(service, value)


def _new_collection() -> dict:
	return {
		"videos": [],
		"documents": [],
		"images": [],
		"audio": [],
		"embeds": [],
		"quizzes": [],
		"assignments": [],
		"programs": [],
		"_text": [],
		"_seen": set(),
	}


def _load_blocks(raw) -> list:
	"""Parse an EditorJS payload, tolerating malformed content."""
	if not raw:
		return []

	if isinstance(raw, dict):
		return raw.get("blocks") or []

	try:
		parsed = json.loads(raw)
	except (ValueError, TypeError):
		return []

	if isinstance(parsed, dict):
		return parsed.get("blocks") or []

	return parsed if isinstance(parsed, list) else []


def _parse_block(block: dict, collected: dict, source: str) -> None:
	if not isinstance(block, dict):
		return

	block_type = block.get("type")
	data = block.get("data") or {}

	if not isinstance(data, dict):
		return

	if block_type == "embed":
		_add_embed(
			collected,
			service=data.get("service"),
			url=data.get("embed") or data.get("source"),
			caption=data.get("caption"),
			source=source,
		)

	elif block_type == "upload":
		_add_file(
			collected,
			file_url=data.get("file_url"),
			declared_type=data.get("file_type"),
			caption=data.get("caption"),
			source=source,
		)
		# The video player supports quizzes pinned to timestamps.
		for row in data.get("quizzes") or []:
			if isinstance(row, dict) and row.get("quiz"):
				_add_unique(collected, "quizzes", row["quiz"], {
					"quiz": row["quiz"],
					"timestamp": row.get("time"),
					"source": source,
				})

	elif block_type in ("image", "simpleImage"):
		file_obj = data.get("file") if isinstance(data.get("file"), dict) else {}
		_add_file(
			collected,
			file_url=data.get("url") or file_obj.get("url"),
			declared_type="image",
			caption=data.get("caption"),
			source=source,
		)

	elif block_type == "quiz" and data.get("quiz"):
		_add_unique(collected, "quizzes", data["quiz"], {
			"quiz": data["quiz"],
			"timestamp": None,
			"source": source,
		})

	elif block_type == "assignment" and data.get("assignment"):
		_add_unique(collected, "assignments", data["assignment"], {
			"assignment": data["assignment"],
			"source": source,
		})

	elif block_type == "program" and data.get("program"):
		_add_unique(collected, "programs", data["program"], {
			"program": data["program"],
			"source": source,
		})

	elif block_type in TEXT_BLOCK_TYPES:
		collected["_text"].append(_block_text(data))


def _block_text(data: dict) -> str:
	"""Flatten a text-ish block into plain text."""
	if data.get("text"):
		return strip_html_tags(str(data["text"]))

	if data.get("code"):
		return ""

	items = data.get("items")
	if isinstance(items, list):
		parts = []
		for item in items:
			if isinstance(item, str):
				parts.append(strip_html_tags(item))
			elif isinstance(item, dict) and item.get("content"):
				parts.append(strip_html_tags(str(item["content"])))
		return " ".join(parts)

	return ""


def _parse_markdown(body: str, collected: dict, source: str) -> None:
	"""Walk legacy markdown, pulling out macros, images and linked documents."""
	for name, argument in MACRO_RE.findall(body):
		argument = _strip_quotes(argument)
		if not argument:
			continue

		if name == "YouTubeVideo":
			_add_embed(collected, service="youtube", url=argument, caption=None, source=source)
		elif name in ("Video", "Audio", "PDF"):
			declared = "pdf" if name == "PDF" else None
			_add_file(collected, file_url=argument, declared_type=declared, caption=None, source=source)
		elif name == "Embed":
			service, _, url = argument.partition("|||")
			_add_embed(collected, service=service, url=url or argument, caption=None, source=source)
		elif name == "Quiz":
			_add_unique(collected, "quizzes", argument, {
				"quiz": argument,
				"timestamp": None,
				"source": source,
			})
		elif name in ("Assignment", "Exercise"):
			_add_unique(collected, "assignments", argument, {
				"assignment": argument,
				"source": source,
			})

	for url in MARKDOWN_IMAGE_RE.findall(body):
		_add_file(collected, file_url=url, declared_type="image", caption=None, source=source)

	# Plain links are only interesting when they point at a real document.
	for url in MARKDOWN_LINK_RE.findall(body):
		if _extension(url) in DOCUMENT_EXTENSIONS:
			_add_file(collected, file_url=url, declared_type=None, caption=None, source=source)

	collected["_text"].append(strip_html_tags(MACRO_RE.sub(" ", body)))


def _add_embed(collected: dict, service, url, caption, source) -> None:
	"""Register an embedded provider asset; YouTube/Vimeo also become videos."""
	if not url:
		return

	service = (service or "").strip().lower() or _guess_service(url)
	normalised = _normalise_embed(service, str(url).strip())

	if not normalised:
		return

	normalised.update({"caption": caption, "source": source})

	bucket = "videos" if normalised["is_video"] else "embeds"
	_add_unique(collected, bucket, f"{bucket}:{normalised['url']}", normalised)


def _normalise_embed(service: str, url: str) -> dict | None:
	if service == "youtube":
		video_id = _youtube_id(url)
		if not video_id:
			return None
		return {
			"provider": "youtube",
			"video_id": video_id,
			"url": f"https://www.youtube.com/watch?v={video_id}",
			"embed_url": f"https://www.youtube.com/embed/{video_id}",
			"thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
			"is_video": True,
		}

	if service == "vimeo":
		match = VIMEO_URL_RE.search(url)
		video_id = match.group(1) if match else None
		return {
			"provider": "vimeo",
			"video_id": video_id,
			"url": url,
			"embed_url": f"https://player.vimeo.com/video/{video_id}" if video_id else url,
			"thumbnail": None,
			"is_video": True,
		}

	return {
		"provider": service or "unknown",
		"video_id": None,
		"url": url,
		"embed_url": url,
		"thumbnail": None,
		"is_video": service in ("cloudflarestream", "bunnystream", "aparat"),
	}


def _guess_service(url: str) -> str:
	lowered = str(url).lower()
	if "youtu" in lowered:
		return "youtube"
	if "vimeo" in lowered:
		return "vimeo"
	if "cloudflarestream" in lowered:
		return "cloudflarestream"
	if "mediadelivery" in lowered or "bunnycdn" in lowered:
		return "bunnystream"
	if "docs.google.com" in lowered or "drive.google.com" in lowered:
		return "google"
	return ""


def _youtube_id(value: str) -> str | None:
	"""Accept a bare 11-char id or any of YouTube's URL shapes."""
	value = (value or "").strip()
	if not value:
		return None

	match = YOUTUBE_URL_RE.search(value)
	if match:
		return match.group(1)

	return value if YOUTUBE_BARE_ID_RE.match(value) else None


def _add_file(collected: dict, file_url, declared_type, caption, source) -> None:
	"""Classify an uploaded/linked asset into documents, images, video or audio."""
	if not file_url:
		return

	file_url = str(file_url).strip()
	if not file_url:
		return

	# A YouTube link can arrive through an upload block in hand-edited content.
	if _guess_service(file_url) == "youtube":
		_add_embed(collected, "youtube", file_url, caption, source)
		return

	extension = _extension(file_url)
	declared = (declared_type or "").strip().lower()
	kind = _classify(extension, declared)

	entry = {
		"file_url": file_url,
		"url": _absolute_url(file_url),
		"file_name": _file_name(file_url),
		"extension": extension,
		"file_type": declared or extension or None,
		"caption": caption,
		"source": source,
		# Filled in later from the File doctype when the asset is managed by Frappe.
		"file_size": None,
		"is_private": None,
	}

	bucket = {
		"document": "documents",
		"image": "images",
		"video": "videos",
		"audio": "audio",
	}.get(kind, "documents")

	if bucket == "videos":
		entry.update({
			"provider": "file",
			"video_id": None,
			"embed_url": entry["url"],
			"thumbnail": None,
			"is_video": True,
		})

	_add_unique(collected, bucket, f"{bucket}:{file_url}", entry)


def _classify(extension: str, declared: str) -> str:
	if declared in ("image", "document", "pdf", "video", "audio"):
		if declared == "pdf":
			return "document"
		return declared

	if extension in IMAGE_EXTENSIONS:
		return "image"
	if extension in VIDEO_EXTENSIONS:
		return "video"
	if extension in AUDIO_EXTENSIONS:
		return "audio"
	if extension in DOCUMENT_EXTENSIONS:
		return "document"

	return "document"


def _extension(url: str) -> str:
	path = urlparse(str(url)).path
	_, _, extension = path.rpartition(".")
	return extension.lower() if extension and extension != path else ""


def _file_name(url: str) -> str:
	path = urlparse(str(url)).path
	return path.rstrip("/").rpartition("/")[2] or url


def _absolute_url(file_url: str) -> str:
	if file_url.startswith(("http://", "https://", "data:")):
		return file_url
	return get_url(file_url)


def _add_unique(collected: dict, bucket: str, key: str, entry: dict) -> None:
	if key in collected["_seen"]:
		return
	collected["_seen"].add(key)
	collected[bucket].append(entry)


def _is_site_file(file_url) -> bool:
	"""True when the asset is hosted by this site and has a File record."""
	return bool(file_url) and str(file_url).startswith(("/files/", "/private/files/"))


def _enrich_with_file_metadata(collected: dict) -> None:
	"""Attach File doctype metadata (size, privacy, name) to site-hosted assets."""
	assets = [
		asset
		for bucket in ("documents", "images", "videos", "audio")
		for asset in collected[bucket]
		if _is_site_file(asset.get("file_url"))
	]

	if not assets:
		return

	file_urls = list({asset["file_url"] for asset in assets})

	records = frappe.get_all(
		"File",
		filters={"file_url": ["in", file_urls]},
		fields=["name", "file_url", "file_name", "file_size", "is_private"],
	)
	by_url = {record.file_url: record for record in records}

	for asset in assets:
		record = by_url.get(asset["file_url"])
		if not record:
			continue
		asset["file_id"] = record.name
		asset["file_name"] = record.file_name or asset["file_name"]
		asset["file_size"] = record.file_size
		asset["is_private"] = bool(record.is_private)


def _build_description(text_parts: list, limit: int = 500) -> str | None:
	"""Condense the lesson's prose into a short plain-text description."""
	text = " ".join(part.strip() for part in text_parts if part and part.strip())
	text = re.sub(r"\s+", " ", text).strip()

	if not text:
		return None

	if len(text) <= limit:
		return text

	return text[:limit].rsplit(" ", 1)[0] + "..."


def _strip_quotes(value: str) -> str:
	value = (value or "").strip()
	if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
		return value[1:-1].strip()
	return value
