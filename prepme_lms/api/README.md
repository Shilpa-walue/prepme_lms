# Prepme LMS API

Versioned HTTP API for the `prepme_lms` app.

```
prepme_lms/
├── api/v1/course.py                    # whitelisted endpoints (thin: validate → call service → envelope)
├── services/course/course_service.py   # course/chapter/lesson aggregation + access control
├── services/course/content_parser.py   # extracts videos, documents & images from lesson bodies
└── utils/response.py                   # consistent success/error envelope
```

The app reads `LMS Course`, `Course Chapter` and `Course Lesson`, which are owned by
the `lms` app — declared via `required_apps` in `hooks.py`.

---

## `GET` Course details

```
/api/method/prepme_lms.api.v1.course.get_course_details?course=<course-id>
```

Returns the complete course tree in a single call: course metadata, instructors,
pricing, certification, related courses, and every chapter with its ordered lessons —
including each lesson's description, YouTube/embedded videos, documents and attachments.

| Param | Default | Description |
| --- | --- | --- |
| `course` | *required* | `LMS Course` id (slug) or exact title |
| `include_content` | `1` | Include raw lesson blocks and markdown body |
| `include_instructor_notes` | `0` | Include instructor-only notes |
| `enforce_access` | `0` | Apply LMS access rules — see below |

A lighter variant, same shape without raw lesson bodies:

```
/api/method/prepme_lms.api.v1.course.get_course_curriculum?course=<course-id>
```

### Example

```bash
curl -H "Authorization: token <api_key>:<api_secret>" \
  "https://your-site.com/api/method/prepme_lms.api.v1.course.get_course_details?course=advanced-calculus"
```

### Response

```jsonc
{
  "success": true,
  "message": "Course details fetched successfully",
  "data": {
    "course": {
      "id": "advanced-calculus",
      "title": "Advanced Calculus",
      "description": "<p>…</p>",
      "short_introduction": "Learn calculus",
      "image": "https://site.com/files/cover.png",
      "intro_video": {
        "provider": "youtube",
        "video_id": "dQw4w9WgXcQ",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
      },
      "tags": ["math", "calculus"],
      "category": "Mathematics",
      "published": true,
      "certification": { "enabled": true, "paid_certificate": false, "evaluator": null },
      "pricing": { "is_paid": true, "amount": 4999, "amount_usd": 60, "currency": "INR" },
      "stats": { "enrollments": 120, "lesson_count": 3, "rating": "4.5" },
      "instructors": [
        { "email": "ada@example.com", "full_name": "Ada Teacher", "user_image": "https://…" }
      ],
      "related_courses": [{ "id": "basic-calculus", "title": "Basic Calculus" }]
    },

    "chapters": [
      {
        "id": "CH-0001",
        "title": "Derivatives",
        "index": 1,
        "lesson_count": 2,
        "scorm": null,
        "lessons": [
          {
            "id": "0001 Intro to Derivatives",
            "title": "Intro to Derivatives",
            "index": 1,
            "include_in_preview": true,
            "content_locked": false,
            "content_format": "blocks",
            "idx": 2,
            "docstatus": 0,
            "owner": "Administrator",
            "modified_by": "Administrator",
            "created_on": "2026-07-16 18:46:10.458123",
            "modified_on": "2026-07-22 00:22:41.806510",

            // short summary for cards/listings (max 500 chars)
            "description": "Short Description Get started with ReactJS by learning what it is…",
            // complete prose, one line per block, never truncated
            "content_text": "Short Description\nGet started with ReactJS…\nLearning Outcome\n…",

            "videos": [
              {
                "provider": "youtube",
                "video_id": "dQw4w9WgXcQ",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "caption": "Lecture 1",
                "source": "content"
              }
            ],

            "documents": [
              {
                "file_url": "/files/notes.pdf",
                "url": "https://site.com/files/notes.pdf",
                "file_name": "notes.pdf",
                "extension": "pdf",
                "file_size": 284512,
                "is_private": false,
                "source": "content"
              }
            ],

            "images": [],
            "audio": [],
            "embeds": [],
            "quizzes": [{ "quiz": "QUIZ-0001", "timestamp": null }],
            "assignments": [],
            "attachments": [
              { "file_name": "worksheet.pdf", "url": "https://…", "source": "lesson_attachment" }
            ],

            "content": [ /* raw EditorJS blocks — only when include_content=1 */ ],
            "body": null
          }
        ]
      }
    ],

    "summary": {
      "total_chapters": 2,
      "total_lessons": 3,
      "total_videos": 4,
      "total_documents": 3,
      "total_quizzes": 1,
      "total_assignments": 0,
      "locked_lessons": 0
    },

    "access": {
      "is_enrolled": true,
      "is_instructor": false,
      "is_moderator": false,
      "has_full_access": true,
      "instructor_notes_included": false
    }
  }
}
```

### Errors

```json
{ "success": false, "message": "Course xyz not found", "error_code": "COURSE_NOT_FOUND" }
```

| Status | `error_code` | Meaning |
| --- | --- | --- |
| 400 | `MISSING_COURSE` | `course` parameter not supplied |
| 403 | `COURSE_ACCESS_DENIED` | Course unpublished and caller may not view it |
| 404 | `COURSE_NOT_FOUND` | No course with that id or title |
| 500 | `INTERNAL_ERROR` | Unexpected failure (logged to the Error Log) |

---

## Implementation notes

**Ordering.** Chapter and lesson order is *not* stored on `Course Chapter` /
`Course Lesson`. It lives on the child rows — `LMS Course.chapters`
(`Chapter Reference`) and `Course Chapter.lessons` (`Lesson Reference`). The service
walks those reference tables, so sequence always matches what the author arranged.
Sorting the chapter/lesson records themselves would produce the wrong order.

**Media extraction.** Lessons store no dedicated video or document fields. Content
lives in `content` (an EditorJS block document) and/or `body` (Markdown with macros).

Both are always scanned — not one or the other. Lessons migrated to the block editor
keep their old markdown, and it can carry macros such as `{{ YouTubeVideo("QFaFIcGhPoM") }}`
that never made it into a block; scanning only the blocks would silently lose them.
Duplicate media is collapsed, so a video present in *both* the embed block and the body
macro is returned once. Its `source` field records where it was found (`content`, `body`,
`youtube_field`, `lesson_attachment`).

Body *prose* is only used for `description` / `content_text` when the lesson has no
blocks — otherwise the same text would be counted twice.

`content_parser` handles:

| Source | Extracted as |
| --- | --- |
| `{"type": "embed", "data": {"service": "youtube", …}}` | video |
| `{"type": "upload", "data": {"file_url", "file_type"}}` | document / image / video / audio, by extension |
| `{{ YouTubeVideo("id \| url") }}` | video |
| `{{ PDF(…) }}`, `{{ Video(…) }}`, `{{ Audio(…) }}` | document / video / audio |
| `{{ Embed("service\|\|\|url") }}` | embed |
| `![alt](url)`, `[text](file.pdf)` | image / document |
| `Course Lesson.youtube` field | video |
| `File` records attached to the lesson | `attachments` |

YouTube ids are normalised from every URL shape (`youtu.be`, `/embed/`, `/shorts/`,
`watch?v=`, bare id), so `{{ YouTubeVideo("QFaFIcGhPoM") }}` and an embed block pointing
at `https://www.youtube.com/embed/QFaFIcGhPoM` both resolve to `video_id: "QFaFIcGhPoM"`
and collapse into a single entry. Each video carries a watch url, embed url and thumbnail.
Site-hosted files are enriched from the `File` doctype with real name, size and privacy.

**Access control.** These endpoints use `frappe.get_all`, which bypasses Frappe's
permission layer, so access is enforced explicitly in `course_service` — and only when
`enforce_access=1` is passed.

> **`enforce_access` defaults to `0`, which returns the full course to anyone who can
> reach the endpoint — including unpublished drafts and paid lesson content, to
> unauthenticated callers.** The endpoints are `allow_guest=True`. That default suits
> trusted server-to-server and admin use. **Pass `enforce_access=1` on any public or
> browser-facing call**, or drop `allow_guest` so a session is always required.

With `enforce_access=1`:

- Unpublished courses → `403` for anyone who is not enrolled, an instructor, or a moderator.
- Lessons not marked `include_in_preview` → `content_locked: true` with empty media
  arrays for users without full access. Titles, ordering and counts stay visible, so the
  curriculum remains browsable without leaking paid content.
- `instructor_notes` → only for that course's instructors and moderators, whatever the
  request asked for.

The `access` block in every response reports what was applied:

```json
"access": {
  "enforced": false,
  "is_enrolled": false, "is_instructor": false,
  "is_moderator": false, "has_full_access": false,
  "instructor_notes_included": false
}
```

Endpoints are rate limited to 60 requests/minute.

**A note on `idx`.** Each lesson carries both `index` and `idx`. Sort on **`index`** —
it is the authored position (1..n) derived from the `Lesson Reference` rows. `idx` is the
raw column on the `Course Lesson` record, is not maintained as a course-wide sequence,
and in real data appears as values like `2, 4, 0, 1, 0, 1`. It is exposed only for
completeness; ordering by it will scramble the curriculum.
