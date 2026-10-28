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
from app.models import IpCheck, Role, User

TEST_PASSWORD = "password-uji-12-karakter"
# Argon2 sengaja lambat; hash sekali saja untuk semua user uji.
_TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


def _test_db_name() -> str:
    return f"{get_settings().db_name}_test"


def _migration_db_name() -> str:
    return f"{get_settings().db_name}_migration_test"


def _assert_test_db(name: str) -> None:
    """Pengaman: operasi destruktif di test hanya boleh menyentuh DB berakhiran `_test`."""
    assert name.endswith("_test"), f"{name!r} bukan database test"
    assert name != get_settings().db_name, "test tidak boleh memakai database dev"


def _ensure_database(name: str) -> Engine:
    """Buat database test jika belum ada, lalu kembalikan engine ke database itu."""
    _assert_test_db(name)
    settings = get_settings()
    admin_engine = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        )
        if not exists:
            quoted = conn.dialect.identifier_preparer.quote(name)
            conn.execute(text(f"CREATE DATABASE {quoted}"))
    admin_engine.dispose()
    return create_engine(settings.database_url.set(database=name))


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    test_engine = _ensure_database(_test_db_name())
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def migration_engine() -> Iterator[Engine]:
    """Database kosong khusus uji migrasi Alembic (`<DB_NAME>_migration_test`).

    Terpisah dari DB `<DB_NAME>_test` agar roundtrip upgrade/downgrade tidak
    merusak skema yang dipakai test lain, dan tidak pernah menyentuh DB dev.
    Skema dikosongkan sebelum tiap test.
    """
    mig_engine = _ensure_database(_migration_db_name())
    assert mig_engine.url.database == _migration_db_name()
    _assert_test_db(mig_engine.url.database)
    with mig_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    yield mig_engine
    mig_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    assert engine.url.database == _test_db_name()
    _assert_test_db(engine.url.database)
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
def make_check(db: Session):
    def _make(
        ip: str = "8.8.8.8", assessment_status: str = "TIDAK_TERSEDIA"
    ) -> IpCheck:
        check = IpCheck(
            ip=ip,
            assessment_status=assessment_status,
            risk_score=None,
            scoring_version="v1-percobaan",
            coverage="0/2",
            flags=[],
            sources=[],
            checked_by="seed",
        )
        db.add(check)
        db.commit()
        return check

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
