"""Pagination tests for list endpoints."""
import uuid

from sqlalchemy import select

from app.models import StudyMaterial


def _create_course(client, headers, code, name="Course"):
    response = client.post(
        "/api/courses", json={"name": name, "code": code}, headers=headers
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_material(client, headers, course_id, title, material_type="notes"):
    response = client.post(
        "/api/materials",
        json={
            "course_id": course_id,
            "title": title,
            "material_type": material_type,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_courses_page_one(client, teacher_auth):
    _, headers = teacher_auth
    for i in range(25):
        _create_course(client, headers, f"CS{i:03d}", name=f"Course {i}")

    response = client.get("/api/courses?page=1&page_size=10", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert len(body["items"]) == 10
    assert body["total"] == 25
    assert body["total_pages"] == 3


def test_courses_last_page(client, teacher_auth):
    _, headers = teacher_auth
    for i in range(25):
        _create_course(client, headers, f"CS{i:03d}", name=f"Course {i}")

    response = client.get("/api/courses?page=3&page_size=10", headers=headers)
    body = response.json()
    assert len(body["items"]) == 5
    assert body["page"] == 3
    assert body["total_pages"] == 3


def test_courses_pagination_no_duplicates_across_pages(client, teacher_auth):
    _, headers = teacher_auth
    for i in range(15):
        _create_course(client, headers, f"CS{i:03d}", name=f"Course {i}")

    page1 = client.get(
        "/api/courses?page=1&page_size=10", headers=headers
    ).json()["items"]
    page2 = client.get(
        "/api/courses?page=2&page_size=10", headers=headers
    ).json()["items"]
    ids1 = {c["id"] for c in page1}
    ids2 = {c["id"] for c in page2}
    assert len(ids1) == 10
    assert len(ids2) == 5
    assert ids1.isdisjoint(ids2)


def test_courses_defaults_to_page_one_size_twenty(client, teacher_auth):
    _, headers = teacher_auth
    for i in range(5):
        _create_course(client, headers, f"CS{i:03d}", name=f"Course {i}")
    body = client.get("/api/courses", headers=headers).json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert len(body["items"]) == 5
    assert body["total"] == 5


def test_page_size_upper_bound_enforced(client, teacher_auth):
    _, headers = teacher_auth
    _create_course(client, headers, "CS001")
    response = client.get("/api/courses?page_size=101", headers=headers)
    assert response.status_code == 422


def test_page_zero_rejected(client, teacher_auth):
    _, headers = teacher_auth
    response = client.get("/api/courses?page=0", headers=headers)
    assert response.status_code == 422


def test_materials_pagination_with_filters(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _create_course(client, headers, "MATH101", name="Math")

    for i in range(3):
        _create_material(client, headers, course_id, f"Notes {i}", "notes")
    for i in range(2):
        _create_material(client, headers, course_id, f"Slides {i}", "ppt")

    response = client.get(
        f"/api/materials?course_id={course_id}&material_type=ppt&page=1&page_size=2",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 2
    assert body["total_pages"] == 1
    assert all(m["material_type"] == "ppt" for m in body["items"])

    response = client.get(
        f"/api/materials?course_id={course_id}&material_type=notes&page=1&page_size=2",
        headers=headers,
    )
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["total_pages"] == 2


def test_materials_pagination_with_status_filter(client, teacher_auth, db):
    _, headers = teacher_auth
    course_id = _create_course(client, headers, "PHY101", name="Physics")

    for i in range(4):
        _create_material(client, headers, course_id, f"Notes {i}")

    material = db.scalar(select(StudyMaterial).order_by(StudyMaterial.id))
    material.status = "processed"
    db.commit()

    response = client.get(
        f"/api/materials?course_id={course_id}&status=processed&page=1&page_size=10",
        headers=headers,
    )
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["status"] == "processed"


def test_materials_pagination_pages(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _create_course(client, headers, "CHE301", name="Chem")

    material_ids = [
        _create_material(client, headers, course_id, f"Material {i}")["id"]
        for i in range(5)
    ]

    response = client.get(
        f"/api/materials?course_id={course_id}&page=1&page_size=3",
        headers=headers,
    )
    body = response.json()
    assert len(body["items"]) == 3
    assert body["total"] == 5
    assert body["total_pages"] == 2
    assert body["page_size"] == 3

    response = client.get(
        f"/api/materials?course_id={course_id}&page=2&page_size=3",
        headers=headers,
    )
    body = response.json()
    assert len(body["items"]) == 2


def test_paginated_materials_have_predictable_keys(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _create_course(client, headers, "CS404", name="CS")
    _create_material(client, headers, course_id, "Algos")

    body = client.get("/api/materials", headers=headers).json()
    assert set(body.keys()) == {
        "items",
        "page",
        "page_size",
        "total",
        "total_pages",
    }