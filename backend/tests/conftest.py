"""Fixture test. Memakai database terpisah `<DB_NAME>_test`, tidak pernah DB dev."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Role, User

TEST_PASSWORD = "password-uji-12-karakter"
# Argon2 sengaja lambat; hash sekali saja untuk semua user uji.
_TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


def _test_db_name() -> str:
    return f"{get_settings().db_name}_test"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    settings = get_settings()
    test_db = _test_db_name()
    # Pengaman: operasi destruktif di bawah hanya boleh menyentuh DB *_test.
    assert test_db.endswith("_test") and test_db != settings.db_name

    admin_engine = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": test_db}
        )
        if not exists:
            quoted = conn.dialect.identifier_preparer.quote(test_db)
            conn.execute(text(f"CREATE DATABASE {quoted}"))
    admin_engine.dispose()

    test_engine = create_engine(settings.database_url.set(database=test_db))
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    assert engine.url.database == _test_db_name()
    with engine.begin() as conn:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def client(engine: Engine, db: Session) -> Iterator[TestClient]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db: Session):
    def _make(
        username: str,
        role: Role = Role.VIEWER,
        *,
        can_send_misp: bool = False,
        is_active: bool = True,
    ) -> User:
        user = User(
            username=username,
            password_hash=_TEST_PASSWORD_HASH,
            role=role.value,
            can_send_misp=can_send_misp,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def login(client: TestClient):
    def _login(username: str, password: str = TEST_PASSWORD) -> dict[str, str]:
        resp = client.post(
            "/api/v1/auth/login", data={"username": username, "password": password}
        )
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login
