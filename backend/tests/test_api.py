import uuid

from tests.conftest import make_auth_headers, register_user

TEST_PASSWORD = "testpassword123"


def create_user(client, headers, name="Alice", email="alice@example.com"):
    return client.post(
        "/api/users", json={"name": name, "email": email}, headers=headers
    )


def create_course(client, headers, name="Databases", code="CS301"):
    return client.post(
        "/api/courses", json={"name": name, "code": code}, headers=headers
    )


def test_root_and_health_endpoints(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "AI Study Material Analyzer API is running",
        "status": "success",
    }

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_user_success(client, teacher_auth):
    _, headers = teacher_auth
    response = create_user(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alice"
    assert body["email"] == "alice@example.com"
    assert body["role"] == "student"
    assert "id" in body
    assert "created_at" in body
    uuid.UUID(body["id"])


def test_create_user_rejects_invalid_email(client, teacher_auth):
    _, headers = teacher_auth
    response = client.post(
        "/api/users",
        json={"name": "Bob", "email": "not-an-email"},
        headers=headers,
    )
    assert response.status_code == 422


def test_create_user_duplicate_email(client, teacher_auth):
    _, headers = teacher_auth
    assert create_user(client, headers).status_code == 201
    response = create_user(client, headers, name="Another Alice")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_get_user(client, teacher_auth):
    _, headers = teacher_auth
    user_id = create_user(client, headers).json()["id"]
    response = client.get(f"/api/users/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_create_course_success(client, teacher_auth):
    _, headers = teacher_auth
    response = create_course(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Databases"
    assert body["code"] == "CS301"
    assert "id" in body
    uuid.UUID(body["id"])


def test_create_course_duplicate_code(client, teacher_auth):
    _, headers = teacher_auth
    assert create_course(client, headers).status_code == 201
    response = create_course(client, headers, name="Databases 2")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_list_courses(client, teacher_auth):
    _, headers = teacher_auth
    create_course(client, headers, name="Alpha", code="A101")
    create_course(client, headers, name="Beta", code="B202")
    response = client.get("/api/courses", headers=headers)
    assert response.status_code == 200
    body = response.json()
    codes = {course["code"] for course in body["items"]}
    assert codes == {"A101", "B202"}
    assert body["total"] == 2
    assert body["total_pages"] == 1


def test_get_course(client, teacher_auth):
    _, headers = teacher_auth
    course_id = create_course(client, headers).json()["id"]
    response = client.get(f"/api/courses/{course_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["code"] == "CS301"


def test_missing_resource_returns_404(client, teacher_auth):
    _, headers = teacher_auth
    missing = str(uuid.uuid4())
    assert client.get(f"/api/users/{missing}", headers=headers).status_code == 404
    assert client.get(f"/api/courses/{missing}", headers=headers).status_code == 404
    assert client.get(f"/api/materials/{missing}", headers=headers).status_code == 404
    assert client.delete(f"/api/materials/{missing}", headers=headers).status_code == 404


def _make_user_and_course(client, headers):
    course_id = create_course(client, headers).json()["id"]
    return course_id


def _create_material(client, headers, course_id, **overrides):
    payload = {
        "course_id": course_id,
        "title": "Chapter 1 Notes",
        "material_type": "notes",
    }
    payload.update(overrides)
    return client.post("/api/materials", json=payload, headers=headers)


def test_create_study_material_success(client, teacher_auth):
    user_id, headers = teacher_auth
    course_id = _make_user_and_course(client, headers)
    response = _create_material(client, headers, course_id)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Chapter 1 Notes"
    assert body["material_type"] == "notes"
    assert body["status"] == "uploaded"
    assert body["course_id"] == course_id
    assert body["uploaded_by"] == str(user_id)
    uuid.UUID(body["id"])


def test_create_study_material_with_optional_fields(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _make_user_and_course(client, headers)
    response = _create_material(
        client,
        headers,
        course_id,
        file_name="chapter1.pdf",
        file_path="/tmp/chapter1.pdf",
        source_url="https://example.com/chapter1.pdf",
        status="processing",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "chapter1.pdf"
    assert body["source_url"] == "https://example.com/chapter1.pdf"
    assert body["status"] == "processing"
    # Filesystem paths are not exposed to clients.
    assert "file_path" not in body
    assert "stored_file_name" not in body


def test_create_study_material_invalid_course_returns_404(client, teacher_auth):
    _, headers = teacher_auth
    _make_user_and_course(client, headers)
    response = _create_material(client, headers, str(uuid.uuid4()))
    assert response.status_code == 404
    assert "Course" in response.json()["detail"]


def test_create_material_requires_teacher(client, teacher_auth):
    _, teacher_headers = teacher_auth
    course_id = _make_user_and_course(client, teacher_headers)

    register_user(client, name="Bob", email="bob@example.com")
    student_headers = make_auth_headers(client, email="bob@example.com")

    response = _create_material(client, student_headers, course_id)
    assert response.status_code == 403


def test_get_study_material(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _make_user_and_course(client, headers)
    material_id = _create_material(client, headers, course_id).json()["id"]
    response = client.get(f"/api/materials/{material_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == material_id


def test_list_study_materials_filter_by_course_id(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _make_user_and_course(client, headers)
    other_course_id = create_course(client, headers, name="OS", code="CS302").json()[
        "id"
]

    _create_material(client, headers, course_id, title="Notes A")
    _create_material(client, headers, other_course_id, title="Notes B")

    response = client.get(f"/api/materials?course_id={course_id}", headers=headers)
    assert response.status_code == 200
    titles = {material["title"] for material in response.json()["items"]}
    assert titles == {"Notes A"}


def test_list_study_materials_filter_by_type_and_status(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _make_user_and_course(client, headers)
    _create_material(client, headers, course_id, material_type="notes")
    _create_material(client, headers, course_id, material_type="ppt")

    response = client.get("/api/materials?material_type=ppt", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["material_type"] == "ppt"
    assert body["total"] == 1

    response = client.get("/api/materials?status=uploaded", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_delete_study_material(client, teacher_auth):
    user_id, headers = teacher_auth
    course_id = _make_user_and_course(client, headers)
    material_id = _create_material(client, headers, course_id).json()["id"]

    response = client.delete(f"/api/materials/{material_id}", headers=headers)
    assert response.status_code == 204

    response = client.get(f"/api/materials/{material_id}", headers=headers)
    assert response.status_code == 404


def test_list_study_materials_empty(client, teacher_auth):
    _, headers = teacher_auth
    response = client.get("/api/materials", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "page_size": 20,
        "total": 0,
        "total_pages": 0,
    }
