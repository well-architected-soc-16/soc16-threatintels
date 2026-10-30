"""Roundtrip migrasi Alembic. Berjalan di DB `<DB_NAME>_migration_test`, bukan DB dev."""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect

from alembic import command
from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_TABLES = {
    "users",
    "audit_logs",
    "ip_checks",
    "ioc_submissions",
    "source_cache",
    "source_calls",
}


def _config(connection) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    # env.py memakai koneksi ini alih-alih engine dev.
    cfg.attributes["connection"] = connection
    return cfg


def _run(engine: Engine, fn, *args) -> None:
    with engine.begin() as connection:
        fn(_config(connection), *args)


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _current_revision(engine: Engine) -> str | None:
    with engine.connect() as conn:
        if "alembic_version" not in inspect(conn).get_table_names():
            return None
        return conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()


def _revisions_newest_first(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        script = ScriptDirectory.from_config(_config(connection))
        return [rev.revision for rev in script.walk_revisions()]


def test_migrasi_tidak_pernah_diarahkan_ke_db_dev(migration_engine):
    name = migration_engine.url.database

    assert name.endswith("_test")
    assert name != get_settings().db_name


def test_upgrade_head_dari_db_kosong_tanpa_drift(migration_engine):
    assert _tables(migration_engine) == set()

    _run(migration_engine, command.upgrade, "head")

    assert _tables(migration_engine) == APP_TABLES | {"alembic_version"}
    assert (
        _current_revision(migration_engine)
        == _revisions_newest_first(migration_engine)[0]
    )
    # Skema hasil migrasi harus identik dengan model (tidak ada drift).
    _run(migration_engine, command.check)


def test_roundtrip_downgrade_per_revisi_lalu_upgrade_lagi(migration_engine):
    _run(migration_engine, command.upgrade, "head")
    revisions = _revisions_newest_first(migration_engine)
    assert len(revisions) >= 3

    # Turun satu revisi demi satu revisi; tiap langkah harus berhasil.
    for expected_previous in [*revisions[1:], None]:
        _run(migration_engine, command.downgrade, "-1")
        assert _current_revision(migration_engine) == expected_previous

    assert _tables(migration_engine) <= {"alembic_version"}

    _run(migration_engine, command.upgrade, "head")

    assert _tables(migration_engine) == APP_TABLES | {"alembic_version"}
    _run(migration_engine, command.check)


def test_downgrade_base_membuang_semua_tabel_aplikasi(migration_engine):
    _run(migration_engine, command.upgrade, "head")

    _run(migration_engine, command.downgrade, "base")

    assert not (_tables(migration_engine) & APP_TABLES)


def test_check_mendeteksi_drift(migration_engine):
    """Pastikan `check` memang bisa gagal: tanpa ini 'tanpa drift' bisa lolos palsu."""
    from alembic.util.exc import CommandError

    _run(migration_engine, command.upgrade, "0002")  # sengaja tidak sampai head

    with pytest.raises(CommandError):
        _run(migration_engine, command.check)
