import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import User
from main import app

TEST_PASSWORD = "testpassword123"

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def _enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def _reset_database() -> None:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


def make_db_user(
    *, name: str, email: str, role: str = "student", password: str = TEST_PASSWORD
) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db = TestingSessionLocal()
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers_for(user: User) -> dict:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def register_user(
    client, name="Alice", email="alice@example.com", password=TEST_PASSWORD
):
    return client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def login_user(client, email="alice@example.com", password=TEST_PASSWORD):
    return client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )


def make_auth_headers(client, email="alice@example.com", password=TEST_PASSWORD):
    response = login_user(client, email=email, password=password)
    assert response.status_code == 200
    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


@pytest.fixture()
def db_session() -> Session:
    _reset_database()
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db():
    """Provide a database session without resetting the schema.

    Useful in API tests that also use the `client` fixture, where the schema
    is already reset by `client` and any `user_auth` data must remain visible.
    """
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client():
    _reset_database()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def user_auth(client):
    """Return (user_id, auth_headers) for a freshly created normal user."""
    user = make_db_user(name="Alice", email="alice@example.com")
    return user.id, auth_headers_for(user)


@pytest.fixture()
def second_user_auth(client):
    """Return (user_id, auth_headers) for a second normal user."""
    user = make_db_user(name="Bob", email="bob@example.com")
    return user.id, auth_headers_for(user)


@pytest.fixture(autouse=True)
def _isolate_rag_store(tmp_path, monkeypatch):
    """Redirect the RAG vector store to a temporary path for every test.

    This prevents any test from touching the real persistent
    ``rag/rag_data/knowledge_base.db`` database. The deterministic embedder is
    pinned so tests are fast and deterministic regardless of whether
    sentence-transformers is installed.
    """
    monkeypatch.setenv("RAG_VECTOR_STORE_PATH", str(tmp_path / "test_vectors.db"))
    monkeypatch.setenv("RAG_EMBEDDING_BACKEND", "deterministic")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()