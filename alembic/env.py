"""Configurazione di Alembic, collegata al nostro progetto."""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# --- Collegamento al nostro progetto ---
from app.config import settings
from app.database import Base
import app.models  # importa TUTTI i modelli, cosi' Alembic li "vede"

config = context.config

# Uso l'URL del database dalla NOSTRA config (locale o produzione),
# invece di quello scritto in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.db_url_normalizzato)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 'target_metadata' dice ad Alembic com'e' fatto lo schema che VOGLIAMO
# (dai nostri modelli). Alembic confronta questo con lo stato reale del DB
# per generare le migrazioni automaticamente.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
