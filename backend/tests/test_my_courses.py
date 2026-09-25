"""Tests for the GET /api/courses/mine endpoint.

Each authenticated user sees only the courses they created (teacher_id = user.id).
"""
import pytest

from tests.conftest import auth_headers_for, make_db_user


def _course(client, headers, name, code):
    return client.post(
        "/api/courses", json={"name": name, "code": code}, headers=headers
    )


# ---------------- Per-user scoping ----------------


def test_user_sees_only_own_courses(client):
    alice = make_db_user(name="Alice", email="alice@example.com")
    bob = make_db_user(name="Bob", email="bob@example.com")
    alice_headers = auth_headers_for(alice)
    bob_headers = auth_headers_for(bob)

    _course(client, alice_headers, "Databases I", "CS301")
    _course(client, bob_headers, "Databases II", "CS302")
    _course(client, alice_headers, "OS", "CS305")

    response = client.get("/api/courses/mine", headers=alice_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    codes = {c["code"] for c in body["items"]}
    assert codes == {"CS301", "CS305"}


def test_user_without_courses_returns_empty(client):
    user = make_db_user(name="Empty", email="empty@example.com")
    headers = auth_headers_for(user)

    response = client.get("/api/courses/mine", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["total_pages"] == 0


# ---------------- Pagination / search ----------------


def test_my_courses_pagination_envelope(client, user_auth):
    _, headers = user_auth
    for i in range(5):
        _course(client, headers, name=f"Course {i}", code=f"MINE{i}")

    response = client.get(
        "/api/courses/mine?page=1&page_size=2", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["total_pages"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2


def test_my_courses_search_scoped(client):
    alice = make_db_user(name="Alice", email="alice@example.com")
    bob = make_db_user(name="Bob", email="bob@example.com")
    alice_headers = auth_headers_for(alice)
    bob_headers = auth_headers_for(bob)

    _course(client, alice_headers, "Databases I", "CS301")
    _course(client, bob_headers, "Databases II", "CS302")

    response = client.get("/api/courses/mine?search=Databases", headers=alice_headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["code"] == "CS301"


# ---------------- Auth required ----------------


def test_my_courses_requires_authentication(client):
    assert client.get("/api/courses/mine").status_code == 401


# ---------------- Envelope consistency ----------------


def test_my_courses_envelope_keys(client, user_auth):
    _, headers = user_auth
    _course(client, headers, "Databases", "CS301")
    body = client.get("/api/courses/mine", headers=headers).json()
    assert set(body.keys()) == {
        "items",
        "page",
        "page_size",
        "total",
        "total_pages",
    }