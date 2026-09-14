# AI Study Material Analyzer — Backend API Integration Guide

This document is the single source of truth for the React frontend (Member 1)
when connecting to the FastAPI backend.

- Base URL: `http://localhost:8000` (dev, see `backend/.env` / `.env.example`).
- Interactive docs (Swagger): `GET /docs`.
- OpenAPI JSON: `GET /openapi.json`.
- All request/response bodies are JSON unless stated otherwise.
- All timestamps are ISO-8601 strings with timezone info.
- All UUIDs are strings (v4).

---

## Authentication

The API uses **JWT bearer tokens**. Public endpoints for signup/login are the
only ones that do not require a token. Every other endpoint requires:

```
Authorization: Bearer <access_token>
```

Roles: `student` and `teacher`. A student can self-register via
`POST /api/auth/register`. Teachers are created by an existing teacher via
`POST /api/users`.

---

### POST /api/auth/register

Public signup. Always creates a `student` account (a client can never
self-assign the `teacher` role).

- Auth: none.
- Role: any.
- Request fields (`application/json`):
  - `name` (string, 1–255, required)
  - `email` (string, valid email, required)
  - `password` (string, 8–128, required)
- Response: `201 Created`, `User` object (see below).
- Important status codes:
  - `201` created
  - `409` email already registered
  - `422` invalid input

### POST /api/auth/login

Exchange credentials for an access token.

- Auth: none.
- Request fields:
  - `email` (string, required)
  - `password` (string, required)
- Response: `200 OK`
  ```json
  {
    "access_token": "<jwt>",
    "token_type": "bearer"
  }
  ```
- Important status codes:
  - `200` ok
  - `401` invalid email or password (identical message for both)

### GET /api/auth/me

Returns the currently authenticated user.

- Auth: Bearer token.
- Role: any.
- Response: `200 OK` `User` object.
- Status codes: `200`, `401`.

### User object

```json
{
  "id": "2a24125f-...",
  "name": "Alice",
  "email": "alice@example.com",
  "role": "student",
  "created_at": "2026-09-13T10:00:00Z"
}
```

Never contains `password`, `password_hash`, or any secret.

---

## Courses

### POST /api/courses

Create a course. The teacher is taken from the token; it can never be supplied
by the client.

- Auth: Bearer token.
- Role: `teacher` only.
- Request fields:
  - `name` (string, 1–255, required)
  - `code` (string, 1–50, required, unique)
  - `description` (string, optional)
- Response: `201 Created`, `Course` object.
- Status codes: `201`, `401`, `403`, `409` (duplicate code), `422`.

### GET /api/courses

List courses. Any authenticated user.

- Auth: Bearer token.
- Role: any.
- Query parameters (all optional):
  - `page` (int, default `1`, min `1`)
  - `page_size` (int, default `20`, min `1`, max `100`)
  - `search` (string, case-insensitive match on name **or** code)
- Response: `200 OK`, paginated envelope:
  ```json
  {
    "items": [ { "Course" }, ... ],
    "page": 1,
    "page_size": 20,
    "total": 123,
    "total_pages": 7
  }
  ```
- Status codes: `200`, `401`, `422` (invalid `page`/`page_size`).

### GET /api/courses/mine

List the caller's own courses, always scoped to the authenticated user.

- Auth: Bearer token.
- Role: any.
- Behavior:
  - **teacher** — returns the courses the teacher owns.
  - **student** — returns the courses the student is enrolled in.
- Query parameters (all optional): `page`, `page_size`, `search` (same
  contract as `GET /api/courses`).
- Response: `200 OK`, same paginated envelope as `GET /api/courses`.
- Status codes: `200`, `401`, `422`.

### GET /api/courses/{course_id}

Get a single course.

- Auth: Bearer token.
- Role: any.
- Response: `200 OK` `Course` object.
- Status codes: `200`, `401`, `404`.

### Course object

```json
{
  "id": "7d6b0f4a-...",
  "name": "Databases",
  "code": "CS301",
  "description": "Intro to relational databases",
  "teacher_id": "2a24125f-...",
  "teacher": {
    "id": "2a24125f-...",
    "name": "Prof. Smith",
    "email": "smith@example.com"
  },
  "created_at": "2026-09-13T10:00:00Z"
}
```

### POST /api/courses/{course_id}/enroll

Enroll the authenticated student in a course.

- Auth: Bearer token.
- Role: `student` only (identity always comes from the token).
- Request body: none (a body is ignored).
- Response: `201 Created`
  ```json
  {
    "id": "897a1c67-...",
    "course_id": "7d6b0f4a-...",
    "student_id": "2a24125f-...",
    "enrolled_at": "2026-09-13T11:00:00Z"
  }
  ```
- Status codes: `201`, `401`, `403`, `404` (course not found), `409` (already
  enrolled).

### DELETE /api/courses/{course_id}/enroll

Remove the authenticated student's own enrollment.

- Auth: Bearer token.
- Role: `student` only.
- Response: `204 No Content`.
- Status codes: `204`, `401`, `403`, `404` (course missing or not enrolled).

### GET /api/courses/{course_id}/enrollments/me

Report whether the authenticated user is enrolled in the course.

- Auth: Bearer token.
- Role: any.
- Response: `200 OK`
  ```json
  {
    "course_id": "7d6b0f4a-...",
    "is_enrolled": true,
    "enrolled_at": "2026-09-13T11:00:00Z"
  }
  ```
- Status codes: `200`, `401`, `404`.

### GET /api/courses/{course_id}/students

List enrolled students with enrollment time.

- Auth: Bearer token.
- Role: `teacher` and only the owner of the course.
- Response: `200 OK`
  ```json
  [
    {
      "id": "2a24125f-...",
      "name": "Alice",
      "email": "alice@example.com",
      "enrolled_at": "2026-09-13T11:00:00Z"
    }
  ]
  ```
- Status codes: `200`, `401`, `403` (not the owning teacher), `404`.

---

## Study Materials

Materials live inside a course. Access rules:
- The **owning teacher** can create, view, download, and delete.
- **Enrolled students** can view and download.
- Everyone else gets `403`.

### POST /api/materials/upload

Upload a file or register a URL-based material. **Multipart form data.**

- Auth: Bearer token.
- Role: `teacher`, and must own `course_id`.
- Form fields (exact names — required unless noted):
  - `course_id` (string UUID, required)
  - `title` (string, 1–255, required)
  - `material_type` (string, 1–50, required; any label e.g. `notes`, `ppt`,
    `video`)
  - `file` (file field, required unless `source_url` is present). Allowed
    extensions: `.pdf`, `.ppt`, `.pptx`, `.doc`, `.docx`, `.txt`, `.png`,
    `.jpg`, `.jpeg`.
  - `source_url` (string, optional, max 2048). Mutually exclusive with `file`.
- Exactly one of `file` or `source_url` must be provided — not neither, not both.
- Response: `201 Created`, `StudyMaterial` object.
- Status codes:
  - `201` created
  - `400` missing/conflicting `file`/`source_url`
  - `401` unauthenticated
  - `403` not the owning teacher
  - `404` course not found
  - `413` file too large (limit from `MAX_UPLOAD_SIZE_MB`)
  - `415` unsupported file type

### POST /api/materials

Create a material record directly (no upload). Typically used for URL-style
materials or legacy rows.

- Auth: Bearer token.
- Role: `teacher`, and must own `course_id`.
- Request fields:
  - `course_id` (UUID, required)
  - `title` (string, 1–255, required)
  - `material_type` (string, 1–50, required)
  - `file_name` (string, optional)
  - `file_path` (string, optional; **accepted but never returned** — internal)
  - `source_url` (string, optional)
  - `status` (enum, optional; default `uploaded`)
- Response: `201 Created`, `StudyMaterial` object.
- Status codes: `201`, `401`, `403`, `404`, `409`, `422`.

### GET /api/materials

List materials the caller may access (own courses for teachers, enrolled
courses for students).

- Auth: Bearer token.
- Role: any.
- Query parameters (all optional):
  - `course_id` (UUID) — restrict to one course; requires ownership/enrollment
  - `material_type` (string)
  - `status` (string: `uploaded`, `processing`, `processed`, `failed`; invalid values produce `422`)
  - `search` (string, case-insensitive match on title **or** original filename)
  - `page` (int, default `1`)
  - `page_size` (int, default `20`, max `100`)
- Response: `200 OK`, paginated envelope (same shape as courses).
- Status codes: `200`, `401`, `403` (filtering another teacher's course),
  `404` (unknown course), `422`.

### GET /api/materials/{material_id}

Get a single material's metadata.

- Auth: Bearer token.
- Role: any, but only owner/enrolled students may see it.
- Response: `200 OK`, `StudyMaterial` object.
- Status codes: `200`, `401`, `403`, `404`.

### GET /api/materials/{material_id}/download

Download the stored file for a material (file-based materials), or metadata for
URL-based materials.

- Auth: Bearer token.
- Role: owner teacher / enrolled student.
- Response:
  - File material: `200 OK`, binary stream with `Content-Disposition:
    attachment; filename="<original name>"`.
  - URL material: `200 OK` JSON
    `{ "material_id": "...", "detail": "This material is URL-based...",
    "source_url": "..." }`.
- Status codes: `200`, `401`, `403`, `404` (material missing or no file).

### DELETE /api/materials/{material_id}

Delete a material and its stored file (if any).

- Auth: Bearer token.
- Role: `teacher`, and must own the material's course.
- Response: `204 No Content`.
- Status codes: `204`, `401`, `403`, `404`.

### StudyMaterial object

```json
{
  "id": "30f7a5d1-...",
  "course_id": "7d6b0f4a-...",
  "uploaded_by": "2a24125f-...",
  "title": "Chapter 1 Notes",
  "material_type": "notes",
  "file_name": "chapter1.pdf",
  "source_url": null,
  "file_size": 204800,
  "mime_type": "application/pdf",
  "status": "uploaded",
  "processed_at": null,
  "error_message": null,
  "created_at": "2026-09-13T12:00:00Z",
  "updated_at": "2026-09-13T12:00:00Z"
}
```

Internal fields never exposed: `password_hash`, `stored_file_name`, `file_path`
(filesystem paths), secrets.

- `processed_at` — ISO-8601 timestamp set when processing completes
  successfully; `null` for freshly uploaded or failed materials.
- `error_message` — human-readable failure description; `null` when
  processing has not failed. Maximum 1 000 characters.

### Material status lifecycle

```
uploaded -> processing -> processed
uploaded/processing -> failed
failed -> processing (retry)
```

Processing is not implemented yet; uploads are always created with
`status = "uploaded"`. The API exposes and accepts only four statuses
(`uploaded`, `processing`, `processed`, `failed`); invalid values on
`POST /api/materials` or `GET /api/materials?status=...` produce `422`.

### POST /api/materials/{material_id}/process

Start (or restart) processing for an existing material. The owning teacher
uses this to transition a freshly uploaded or previously failed material
into the `processing` state, signalling a future processing worker to pick
the material up.

No processing is actually performed by this endpoint; it only updates the
material's status.

- Auth: Bearer token.
- Role: `teacher`, and must own the material's course.
- Response: `200 OK`, updated `StudyMaterial` object (status = `processing`).
- Status codes:
  - `200` status transitioned
  - `401` unauthenticated
  - `403` not the owning teacher
  - `404` material not found
  - `409` material is not in a startable state (already `processing` or `processed`)

---

## Users (teacher-managed)

### POST /api/users

Create a user (typically a teacher account).

- Auth: Bearer token.
- Role: `teacher`.
- Request fields: `name` (1–255), `email` (valid email).
- Response: `201 Created`, `User`.
- Status codes: `201`, `401`, `403`, `409`, `422`.

### GET /api/users/{user_id}

- Auth: Bearer token.
- Role: `teacher` only (limits enumeration).
- Response: `200 OK`, `User`.
- Status codes: `200`, `401`, `403`, `404`.

---

## Health

### GET /health

Liveness: the process is running. Never touches the database. Always `200`.

### GET /health/database

Database health: PostgreSQL answers `SELECT 1`.
- `200` `{ "status": "healthy", "database": "connected" }`
- `503` `{ "status": "unhealthy", "database": "unavailable" }`

### GET /health/ready

Readiness: the app is ready to serve requests (database availability).
- `200` `{ "status": "ready", "database": "connected" }`
- `503` `{ "status": "not_ready", "database": "unavailable" }`

Differences:
- **Liveness**: "is the process up?" — always reaches the HTTP layer.
- **Database health**: "is the DB dependency reachable?"
- **Readiness**: "should traffic be routed here?" — currently equivalent to
  database health.

---

## Error responses

All handled errors keep FastAPI's standard `detail` field and add a
machine-readable `error` envelope:

```json
{
  "detail": "Course with id 7d6b0f4a-... was not found",
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Course with id 7d6b0f4a-... was not found"
  }
}
```

Status codes and codes:

| Status | Meaning                  | `error.code`                 |
|--------|--------------------------|------------------------------|
| 400    | Bad request              | `BAD_REQUEST`                |
| 401    | Unauthenticated          | `UNAUTHORIZED`               |
| 403    | Forbidden                | `FORBIDDEN`                  |
| 404    | Not found                | `RESOURCE_NOT_FOUND`         |
| 409    | Duplicate resource       | `CONFLICT`                   |
| 413    | Upload too large         | `REQUEST_ENTITY_TOO_LARGE`   |
| 415    | Unsupported media type   | `UNSUPPORTED_MEDIA_TYPE`     |
| 422    | Validation error         | `VALIDATION_ERROR`           |
| 500    | Unhandled internal error | `INTERNAL_SERVER_ERROR`      |
| 503    | Dependency unavailable   | `SERVICE_UNAVAILABLE`        |

422 responses keep FastAPI's standard `detail` array unchanged (list of
per-field errors), plus the `error` envelope.

Error bodies never contain passwords, secrets, filesystem paths, SQL, or stack
traces. Unhandled database failures (`SQLAlchemyError`) and file-storage
failures (`OSError`) also return this JSON envelope with status `500`; the
detailed cause is written to server logs only.

---

## Pagination

`GET /api/courses` and `GET /api/materials` return a stable envelope:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "total_pages": 0
}
```

- `page` >= 1
- `page_size` 1–100 (default 20)
- `total` = matching rows before paging
- `total_pages` = ceil(total / page_size); `0` when `total == 0`

---

## CORS

Configured via the `CORS_ORIGINS` environment variable
(comma-separated list, default is the local Vite dev server). Example:

```
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

The API supports credentials on configured origins. Do not use `*` in
production — when a wildcard is configured, credentials are disabled.

---

## Local development: PostgreSQL, Alembic, and integration tests

The backend targets **PostgreSQL** (driver: `psycopg`). The application is
configured purely through environment variables (see `backend/.env.example`);
credentials are never hard-coded in source files.

### PostgreSQL setup

1. Install and start PostgreSQL on your machine (e.g. the EDB installer on
   Windows) and make sure `psql` is on your `PATH`.
2. Create a dedicated local development database:
   ```
   createdb ai_study_material_analyzer_dev
   ```
   Recommended location is the local `backend/.env` (kept out of Git):
   ```
   DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/ai_study_material_analyzer_dev
   ```

### Environment variables (backend)

| Variable              | Purpose                                                | Required |
|-----------------------|--------------------------------------------------------|----------|
| `DATABASE_URL`        | SQLAlchemy connection URL for the application database | yes      |
| `STORAGE_DIR`         | Directory for uploaded files (`./storage` by default) | no       |
| `MAX_UPLOAD_SIZE_MB`  | Upload size limit in MB (`20` by default)             | no       |
| `JWT_SECRET_KEY`      | Signing secret for access tokens                      | yes*     |
| `JWT_ALGORITHM`       | Token algorithm (`HS256` by default)                  | no       |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime (`60` by default)        | no       |
| `CORS_ORIGINS`        | Comma-separated allowed browser origins               | no       |
| `TEST_DATABASE_URL`   | Separate PostgreSQL URL for the integration tests     | only for integration tests |

`*` Development-only default exists; always set it for real environments.

### Running Alembic migrations

From the `backend/` directory (with `DATABASE_URL` exported or set in
`backend/.env`):

```
alembic current          # show current revision
alembic upgrade head     # apply all pending migrations (0001 -> 0004)
alembic check            # verify migrations match the models (needs a DB)
```

Expected migration chain: `0001_initial_schema -> 0002_study_material_file_metadata
-> 0003_add_user_auth_fields -> 0004_course_ownership_and_enrollments` (the
current head).

### PostgreSQL-backed integration tests

The unit test suite (`pytest`) runs against an in-memory SQLite database and
needs no setup; it passes with zero database configuration:

```
pytest
```

Live-PostgreSQL integration tests live in `tests/test_postgres_integration.py`
and are **skipped automatically** when `TEST_DATABASE_URL` is not set. To
actually run them:

1. Create a dedicated test database:
   ```
   createdb ai_study_material_analyzer_test
   ```
2. Run with the application pointed at a live PostgreSQL instance:
   ```
   TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/ai_study_material_analyzer_test \
   pytest tests/test_postgres_integration.py -v --tb=short
   ```

Notes:

- `TEST_DATABASE_URL` must point at PostgreSQL; the integration tests refuse
  SQLite so they cannot silently stand in for a real database.
- The application `DATABASE_URL` is defaulted to `TEST_DATABASE_URL` for the
  duration of the integration run so `/health/database` and `/health/ready`
  reflect the live database. Export `DATABASE_URL` explicitly to use a
  different connection.
- These tests never run destructive `DROP DATABASE` operations. Each test only
  drops and recreates the tables inside the pre-existing test database, which
  is safe on a database created specifically for testing.