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
| `include_instructor_notes` | `0` | Include instructor-only notes (privileged) |

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
            "description": "Understanding derivatives and rates of change…",

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
lives either in `content` (an EditorJS block document) or, for older lessons, in
`body` as Markdown with macros. `content_parser` handles both:

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
`watch?v=`, bare id) and each video is returned with a watch url, embed url and
thumbnail. Assets are deduplicated, so the same video referenced two ways appears once.
Site-hosted files are enriched from the `File` doctype with real name, size and privacy.

**Access control.** These endpoints use `frappe.get_all`, which bypasses Frappe's
permission layer, so access is enforced explicitly in `course_service`:

- Unpublished courses → visible only to enrolled members, course instructors, moderators.
- Lessons not marked `include_in_preview` → returned with `content_locked: true` and
  empty media arrays for users without full access. Titles and ordering stay visible so
  the curriculum remains browsable without leaking paid content.
- `instructor_notes` → returned only to that course's instructors and moderators,
  regardless of the request parameter.

Endpoints are rate limited to 60 requests/minute.
