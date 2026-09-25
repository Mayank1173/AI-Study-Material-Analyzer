# AI Study Material Analyzer — Backend API Integration Guide

This document is the single source of truth for the React frontend when
connecting to the FastAPI backend.

- Base URL: `http://localhost:8000` (dev, see `backend/.env` / `.env.example`).
- Interactive docs (Swagger): `GET /docs`.
- OpenAPI JSON: `GET /openapi.json`.
- All request/response bodies are JSON unless stated otherwise.
- All timestamps are ISO-8601 strings with timezone info.
- All UUIDs are strings (v4).

---

## Model: a single normal-user workflow

There are no teacher/student roles and no account-type selection at signup.
Every account is a normal user who can:

- create their own subjects (`Course` rows),
- upload study materials to any subject,
- view/download/delete/process **only their own** uploads,
- chat with the RAG engine, which answers **only from their own** materials.

Subjects act as collections (e.g. `DBMS`, `OS`, `DAA`) for organizing uploaded
notes. A user's subject list comes from `GET /api/courses/mine` (subjects they
created); new subjects are created on the fly via `POST /api/courses` (the
frontend does this inline from the Upload page).

All resources are owner-scoped. `course_id` and `material_id` filters only
narrow the authenticated user's own scope — they can never broaden it.

---

## Authentication

The API uses **JWT bearer tokens**. Public endpoints for signup/login are the
only ones that do not require a token. Every other endpoint requires:

```
Authorization: Bearer <access_token>
```

The authenticated user's id is always taken from the JWT — never from a request
body, query parameter, or header the client controls.

### POST /api/auth/register

Public signup. Creates a normal user account. The backend persistence layer
keeps a legacy `role` column (default `student`) for backward compatibility,
but it is never exposed to clients and never used for authorization.

- Auth: none.
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
- Response: `200 OK` `User` object.
- Status codes: `200`, `401`.

### User object

```json
{
  "id": "2a24125f-...",
  "name": "Alice",
  "email": "alice@example.com",
  "created_at": "2026-09-13T10:00:00Z"
}
```

Never contains `role`, `password`, `password_hash`, or any secret.

---

## Courses (Subjects)

A `Course` represents a subject/collection owned by the user who created it
(`teacher_id` column, kept for backward compatibility, is the owner).

### POST /api/courses

Create a subject. The owner is taken from the token and can never be supplied
by the client. Any authenticated user.

- Auth: Bearer token.
- Request fields:
  - `name` (string, 1–255, required)
  - `code` (string, 1–50, required)
  - `description` (string, optional)
- Response: `201 Created`, `Course` object.
- Status codes: `201`, `401`, `409` (the caller already owns a subject with
  that code), `422`.

Note on uniqueness: codes are unique **per owner**, not globally. Two different
users can use the same code; a single user cannot repeat a code.

### GET /api/courses

List all subjects. Any authenticated user.

- Auth: Bearer token.
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

List the subjects **created by the authenticated user**, always scoped to the
token's identity.

- Auth: Bearer token.
- Query parameters (all optional): `page`, `page_size`, `search` (same
  contract as `GET /api/courses`).
- Response: `200 OK`, same paginated envelope as `GET /api/courses`.
- Status codes: `200`, `401`, `422`.

### GET /api/courses/{course_id}

Get a single subject.

- Auth: Bearer token.
- Response: `200 OK` `Course` object.
- Status codes: `200`, `401`, `404`.

### Course object

```json
{
  "id": "7d6b0f4a-...",
  "name": "Database Management Systems",
  "code": "DBMS",
  "description": "Intro to relational databases",
  "created_at": "2026-09-13T10:00:00Z"
}
```

---

## Study Materials

Materials belong to a subject (`course_id`) but are owned **privately** by the
user who uploaded them (`uploaded_by`, always from the token). Access rules:

- Any authenticated user can upload to any existing subject.
- A user can view, download, process, or delete **only their own uploads**.
- Accessing another user's material returns `403`.

### Supported file types

Materials are indexed by the RAG pipeline, which can extract text from exactly
these formats:

- `.pdf`
- `.docx`
- `.pptx`
- `.txt`

Legacy Office formats (`.doc`, `.ppt`) and image formats (`.png`, `.jpg`,
`.jpeg`) are **rejected at upload time** with `415 Unsupported Media Type`.
There is no OCR or legacy Office extraction.

### POST /api/materials/upload

Upload a study-material file. **Multipart form data.**

- Auth: Bearer token.
- Form fields (exact names — required unless noted):
  - `course_id` (string UUID, required; the subject must exist)
  - `title` (string, 1–255, required)
  - `material_type` (string, 1–50, required; a label such as `notes`,
    `ppt`, `quiz`, `other`)
  - `file` (file field, required; one of the supported types above) **or**
    `source_url` (string, optional, max 2048; legacy API-only, see below).
- Exactly one of `file` or `source_url` must be provided — not neither, not both.
- Response: `201 Created`, `StudyMaterial` object.
- Status codes:
  - `201` created
  - `400` missing/conflicting `file`/`source_url`
  - `401` unauthenticated
  - `404` course not found
  - `413` file too large (limit from `MAX_UPLOAD_SIZE_MB`, default 20 MB)
  - `415` unsupported file type
  - `422` invalid input

> **URL materials are legacy/API-only.** They can still be registered through
> this endpoint, but a URL material has no stored file and **cannot be
> processed or indexed** by the RAG pipeline (processing marks it `failed`).
> The current frontend only uploads files and never creates URL materials.

### POST /api/materials

Create a material record directly (no upload). Used for legacy rows or
test/seed data.

- Auth: Bearer token.
- The uploader identity is taken from the token, never from the body.
- Request fields:
  - `course_id` (UUID, required)
  - `title` (string, 1–255, required)
  - `material_type` (string, 1–50, required)
  - `file_name` (string, optional)
  - `file_path` (string, optional; **accepted but never returned** — internal)
  - `source_url` (string, optional)
  - `status` (enum, optional; default `uploaded`)
- Response: `201 Created`, `StudyMaterial` object.
- Status codes: `201`, `401`, `404` (course not found), `422`.

### GET /api/materials

List the materials **uploaded by the authenticated user**.

- Auth: Bearer token.
- Query parameters (all optional):
  - `course_id` (UUID) — restrict to one subject
  - `material_type` (string)
  - `status` (string: `uploaded`, `processing`, `processed`, `failed`;
    invalid values produce `422`)
  - `search` (string, case-insensitive match on title **or** original filename)
  - `page` (int, default `1`)
  - `page_size` (int, default `20`, max `100`)
- Response: `200 OK`, paginated envelope (same shape as courses).
- Status codes: `200`, `401`, `404` (unknown `course_id`), `422`.

### GET /api/materials/{material_id}

Get a single material's metadata.

- Auth: Bearer token.
- Only the uploader may see it.
- Response: `200 OK`, `StudyMaterial` object.
- Status codes: `200`, `401`, `403`, `404`.

### GET /api/materials/{material_id}/download

Download the stored file for a material (file-based materials), or metadata for
legacy URL materials.

- Auth: Bearer token.
- Only the uploader may download it.
- Response:
  - File material: `200 OK`, binary stream with `Content-Disposition:
    attachment; filename="<original name>"`.
  - URL material: `200 OK` JSON
    `{ "material_id": "...", "detail": "This material is URL-based...",
    "source_url": "..." }`.
- Status codes: `200`, `401`, `403`, `404` (material missing or no file),
  `500` (stored-file reference is invalid).

### POST /api/materials/{material_id}/process

Start (or restart) processing for an existing material: it is indexed into the
RAG knowledge base.

- Auth: Bearer token.
- Only the uploader may trigger processing.
- Only freshly uploaded (`uploaded`) or failed (`failed`) materials can start
  processing. Attempting to start on an already `processing` or `processed`
  material returns `409`.
- Response: `200 OK`, updated `StudyMaterial` object — `processing` on success,
  or `processed`/`failed` if the operation completed in-line.
- Status codes:
  - `200` service executed (inspect `status` for outcome)
  - `401` unauthenticated
  - `403` not the uploader
  - `404` material not found
  - `409` material is not in a startable state

### Automatic upload → processing

Uploading a file creates the material with `status = "uploaded"`. The frontend
then immediately calls `POST /api/materials/{id}/process` for each uploaded
material, so from the user's perspective upload and indexing happen together.
There is no background worker; processing runs synchronously in the request.

### Material status values and lifecycle

A material moves through a small state machine. The API exposes and accepts
only four statuses:

```
uploaded -> processing -> processed
uploaded/processing -> failed
failed -> processing (retry)
```

| Status        | Meaning                                                            |
|---------------|--------------------------------------------------------------------|
| `uploaded`    | File stored; not yet processed (or awaiting a process call).       |
| `processing`  | Indexing in progress.                                              |
| `processed`   | Successfully indexed; searchable by the chat engine.               |
| `failed`      | Indexing failed; `error_message` holds a safe, truncated reason.   |

- `processed_at` — ISO-8601 timestamp set when processing completes
  successfully; `null` for freshly uploaded or failed materials.
- `error_message` — a human-readable, truncated (1000 chars) failure
  description; `null` when processing has not failed.

**Retry behavior:** failed materials can be retried with
`POST /api/materials/{id}/process`; a retry re-runs indexing and, on success,
replaces the material's prior chunks (re-indexing is idempotent — it never
duplicates).

### DELETE /api/materials/{material_id}

Delete a material, its stored file, and its RAG index chunks.

- Auth: Bearer token.
- Only the uploader may delete it.
- Response: `204 No Content`.
- Status codes: `204`, `401`, `403`, `404`.

Deletion performs best-effort RAG cleanup: every chunk owned by the material is
removed from the knowledge base, so a deleted material is no longer searchable.

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
  "status": "processed",
  "processed_at": "2026-09-13T12:00:00Z",
  "error_message": null,
  "created_at": "2026-09-13T12:00:00Z",
  "updated_at": "2026-09-13T12:00:00Z"
}
```

Internal fields never exposed: `password_hash`, `stored_file_name`, `file_path`
(filesystem paths), secrets.

---

## Chat

### POST /api/chat

Answer a question grounded in the authenticated user's own indexed study
materials (RAG).

- Auth: Bearer token (required).
- **The user id always comes from the JWT**, never from the request body.
- Request body (`application/json`):

  **ChatRequest**

  | Field          | Type   | Required | Description                                          |
  |----------------|--------|----------|------------------------------------------------------|
  | `message`      | string | yes      | The student's question, 1–4000 characters.           |
  | `course_id`    | string | no       | UUID; restrict retrieval to one subject. Only narrows the user's own index. |
  | `material_id`  | string | no       | UUID; restrict retrieval to one material. Only narrows the user's own index. |

- Response: `200 OK`

  **ChatResponse**

  ```json
  {
    "answer": "Plants convert light energy into chemical energy...",
    "sources": [
      {
        "source_index": 1,
        "material_id": "30f7a5d1-...",
        "course_id": "7d6b0f4a-...",
        "material_title": "Chapter 1 Notes",
        "original_filename": "chapter1.pdf",
        "source_location": "Page 3",
        "score": 0.84
      }
    ],
    "has_context": true
  }
  ```

  | Field          | Type   | Description                                              |
  |----------------|--------|----------------------------------------------------------|
  | `answer`       | string | The generated answer.                                    |
  | `sources`      | array  | Retrieved chunk references used to ground the answer. Empty when no material matched. |
  | `has_context`  | bool   | False when nothing was retrieved from the user's index.  |

  Each source references the material and subject the chunk came from, the
  human-readable title/filename, a location hint (e.g. page), and a relevance
  score between 0 and 1 (higher is more relevant).

- Status codes:
  - `200` success (check `has_context` for whether material was found)
  - `401` unauthenticated
  - `422` empty or over-long `message`
  - `500` knowledge-base failure
  - `503` knowledge base temporarily unavailable

### Security / ownership

- Authentication is mandatory (JWT Bearer token).
- `user_id` is derived from the JWT and passed to the retrieval layer; a
  client cannot spoof another user's id.
- `course_id`/`material_id` filters are applied **on top of** the
  user-scoped index. They only ever narrow the authenticated user's own
  materials.
- The retrieved text is wrapped as data (not instructions) in the prompt to
  mitigate prompt injection; answers are grounded in the retrieved material.

### No context

When no chunks match (or the user has no indexed material), the API returns
`200` with `has_context: false`, an empty `sources` array, and a safe
no-context message in `answer`.

### POST /api/chat/summary

Generate an **AI study summary** for a subject, grounded only in the
authenticated user's own processed study material (RAG).

- Auth: Bearer token (required).
- **The user id always comes from the JWT**, never from the request body.
- Request body (`application/json`):

  **SummaryRequest**

  | Field       | Type   | Required | Description                                                                |
  |-------------|--------|----------|----------------------------------------------------------------------------|
  | `course_id` | string | no       | UUID of the subject (course) to summarize. Restricts retrieval to that subject's material in the user's own index. |

- Response: `200 OK`

  **SummaryResponse**

  ```json
  {
    "summary": "# Biology\n\n**Overview:** ... [Source 1] ...",
    "sources": [
      {
        "source_index": 1,
        "material_id": "30f7a5d1-...",
        "course_id": "7d6b0f4a-...",
        "material_title": "Chapter 1 Notes",
        "original_filename": "chapter1.pdf",
        "source_location": "Page 3",
        "score": 0.84
      }
    ],
    "has_context": true
  }
  ```

  | Field         | Type   | Description                                              |
  |---------------|--------|----------------------------------------------------------|
  | `summary`     | string | The generated study summary.                             |
  | `sources`     | array  | Retrieved chunk references used to ground the summary. Empty when no material was found. |
  | `has_context` | bool   | False when nothing was retrieved from the user's index.  |

- Status codes:
  - `200` success (check `has_context` for whether material was found)
  - `401` unauthenticated
  - `422` invalid `course_id`
  - `500` knowledge-base failure
  - `503` knowledge base temporarily unavailable

The summary prompt forces the model to organize the response for studying
(subject overview, important topics, key concepts, definitions/formulas/key
points, connections between topics, and exam-relevant concepts only when the
material supports them), to answer only from the retrieved material, and never
to fabricate missing facts. When no processed material exists for the subject,
the endpoint returns `200` with `has_context: false`, an empty `sources`
array, and a clear no-material message. When material was retrieved but the
LLM is unavailable, the endpoint returns `200` with `has_context: true`, the
retrieved sources, and the standard "temporarily unavailable" message.

### Security / ownership (shared by /api/chat and /api/chat/summary)

- Authentication is mandatory (JWT Bearer token).
- `user_id` is derived from the JWT and passed to the retrieval layer; a
  client cannot spoof another user's id.
- `course_id`/`material_id` filters are applied **on top of** the
  user-scoped index. They only ever narrow the authenticated user's own
  materials.
- The retrieved text is wrapped as data (not instructions) in the prompt to
  mitigate prompt injection; summaries and answers are grounded in the
  retrieved material.

### No context (shared)

When no chunks match (or the user has no indexed material), the API returns
`200` with `has_context: false`, an empty `sources` array, and a safe
no-context message (in `answer` for chat, `summary` for the summary endpoint).

### Ollama configuration

The chat endpoint uses an LLM provider selected by the backend settings:

| Variable                   | Default                  | Purpose                                            |
|----------------------------|--------------------------|----------------------------------------------------|
| `LLM_PROVIDER`             | `ollama`                 | `"ollama"` (default) or `"mock"` (for tests).      |
| `LLM_MODEL`                | `qwen2.5-coder:7b`       | Ollama model tag.                                  |
| `LLM_THINK`                | `false`                  | Extended thinking/reasoning for Qwen3-class models (unused by the default qwen2.5-coder). |
| `LLM_TIMEOUT_SECONDS`      | `120`                    | Timeout (seconds) for LLM generation requests.     |
| `LLM_MAX_TOKENS`           | `512`                    | Max generated tokens for a normal chat answer (ceiling, not a target). |
| `OLLAMA_BASE_URL`          | `http://127.0.0.1:11434` | Local Ollama HTTP API base URL.                    |

Start Ollama locally with the default model pulled, e.g.:

```
ollama serve
ollama pull qwen2.5-coder:7b
```

The default model `qwen2.5-coder:7b` answers directly without a thinking
phase. `LLM_THINK` (default `false`, kept for backward compatibility) sends
`"think": false` (top-level) in the `/api/chat` request so any Qwen3-class
model configured via `LLM_MODEL` answers without a long reasoning phase;
`LLM_TIMEOUT_SECONDS` bounds how long a generation may take before the request
is aborted and the safe "language model temporarily unavailable" response is
returned. `LLM_MAX_TOKENS` caps the generated length for a normal answer; study
summaries use their own larger budget and are unaffected.

### Behavior when Ollama is unavailable

If the LLM provider fails during answer generation, the endpoint still returns
`200 OK`. When material was retrieved but the model cannot be reached, the
answer is:

```
The language model is temporarily unavailable. Please try again later.
```

with `has_context: true` and the retrieved `sources` intact. When nothing was
retrieved, the standard no-context message is returned. The mock provider
(`LLM_PROVIDER=mock`) is used by the automated test suite and requires no
Ollama server.

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

`GET /api/courses`, `GET /api/courses/mine` and `GET /api/materials` return a
stable envelope:

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

## Local development: PostgreSQL, Alembic, RAG, and integration tests

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
| `LLM_PROVIDER`        | `"ollama"` or `"mock"` (chat LLM backend)             | no       |
| `LLM_MODEL`           | Ollama model tag (e.g. `qwen2.5-coder:7b`)            | no       |
| `LLM_THINK`           | Enable Qwen3-style thinking (`true`/`false`, default `false`) | no |
| `LLM_TIMEOUT_SECONDS` | LLM generation timeout in seconds (default `120`)     | no       |
| `LLM_MAX_TOKENS` | Max tokens for a normal chat answer (default `512`, ceiling) | no |
| `OLLAMA_BASE_URL`     | Ollama HTTP API base URL                              | no       |
| `RAG_VECTOR_STORE_PATH` | SQLite vector-store file (default: `rag/rag_data/knowledge_base.db`) | no |
| `RAG_EMBEDDING_BACKEND` | `"auto"` (default), `"deterministic"`, `"sentence-transformers"` | no |
| `RAG_EMBEDDING_MODEL` | Embedding model for sentence-transformers (`all-MiniLM-L6-v2`) | no |
| `TEST_DATABASE_URL`   | Separate PostgreSQL URL for the integration tests     | only for integration tests |

`*` Development-only default exists; always set it for real environments.

### RAG embedding configuration

The knowledge base embeds document chunks for semantic search:

- `RAG_EMBEDDING_BACKEND=auto` (the default) uses
  `sentence-transformers` with `all-MiniLM-L6-v2` (384-dim) when it is
  installed, and falls back to the dependency-free, deterministic embedder
  (128-dim) otherwise.
- `RAG_EMBEDDING_BACKEND=deterministic` always uses the offline deterministic
  embedder (used by the automated tests and fully offline environments).
- `RAG_EMBEDDING_BACKEND=sentence-transformers` always requires the real model.

**IMPORTANT — one-time local reset when changing embeddings:** the SQLite
vector store pins its embedding dimension on the first insert. Switching from
the deterministic 128-dim vectors to the MiniLM 384-dim vectors (or vice versa)
requires deleting the local SQLite store once so it is recreated with the new
dimension. This is the local file only:

```
rag/rag_data/knowledge_base.db
```

It is git-ignored and safe to delete. PostgreSQL data lives in a separate
database and is never touched by this reset.

### Running Alembic migrations

From the `backend/` directory (with `DATABASE_URL` exported or set in
`backend/.env`):

```
alembic current          # show current revision
alembic upgrade head     # apply all pending migrations (0001 -> 0006)
alembic check            # verify migrations match the models (needs a DB)
```

Expected migration chain: `0001_initial_schema -> 0002_file_metadata
-> 0003_add_user_auth_fields -> 0004_enrollments -> 0005_processing_lifecycle
-> 0006_courses_code_not_unique` (the current head).

`0006_courses_code_not_unique` drops the global unique constraint on
`courses.code` so codes can be reused per-owner. The `users.role` column and
the `course_enrollments` table remain in the schema for backward
compatibility; they are no longer used by the application logic.

### Running tests

A root `pytest.ini` configures the import paths, so the suites run from the
repository root with the backend virtual environment — no manual `PYTHONPATH`
needed:

```
# Use the backend virtual environment's interpreter (backend/.venv).
python -m pytest rag/tests -q
python -m pytest backend/tests -q
```

The unit suites run against in-memory SQLite and need no database setup.

### PostgreSQL-backed integration tests

Live-PostgreSQL integration tests live in `backend/tests/test_postgres_integration.py`
and are **skipped automatically** when `TEST_DATABASE_URL` is not set. To
actually run them:

1. Create a dedicated test database:
   ```
   createdb ai_study_material_analyzer_test
   ```
2. Run with the application pointed at a live PostgreSQL instance:
   ```
   TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/ai_study_material_analyzer_test \
   python -m pytest backend/tests/test_postgres_integration.py -q
   ```
   (On Windows PowerShell, set `$env:TEST_DATABASE_URL=...` before running.)

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