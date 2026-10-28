from logging.config import fileConfig

from alembic import context

# Import model supaya terdaftar di metadata (dipakai autogenerate / alembic check).
from app import models  # noqa: F401
from app.core.config import get_settings
from app.db import base
from app.db.session import get_engine

config = context.config
if config.config_file_name is not None:
    # Jangan menonaktifkan logger aplikasi saat Alembic dipanggil dari dalam proses (test).
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = base.Base.metadata


def run_migrations_offline() -> None:
    # Password disamarkan; offline mode hanya butuh dialek untuk membuat SQL.
    url = get_settings().database_url.render_as_string(hide_password=True)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Pemanggil programatik (test) boleh menyuntikkan koneksinya sendiri, sehingga
    # migrasi berjalan di DB yang dipilih pemanggil, bukan di engine dev.
    injected = config.attributes.get("connection")
    if injected is not None:
        _run(injected)
        return
    with get_engine().connect() as connection:
        _run(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
