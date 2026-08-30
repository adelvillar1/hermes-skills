"""Alembic async env.py template for SQLAlchemy 2.0 + aiosqlite.

Key gotcha: sys.path.insert is required because Alembic runs from the
project root, not from apps/api/. Without it, `from src.db.models import *`
fails with ModuleNotFoundError.

Usage:
  cd apps/api
  uv run alembic revision --autogenerate -m "description"
  uv run alembic upgrade head
"""
from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

# REQUIRED: ensure apps/api/ is on sys.path so `src.*` imports resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Import ALL ORM models so Alembic's autogenerate detects them.
# The noqa suppresses unused-import and wildcard-import warnings.
from src.db.models import *  # noqa: F401, F403
from src.db.models.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generate SQL without DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Configure and run migrations on a live connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode — the production path."""
    from src.config import get_settings

    settings = get_settings()
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connect to DB and apply."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
