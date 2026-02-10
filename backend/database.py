"""
Database engine and session factory using SQLAlchemy async.
Supports both Azure SQL (production) and SQLite (local dev).
"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_config

engine = None
async_session_factory = None


class Base(DeclarativeBase):
    pass


def get_engine():
    global engine
    if engine is None:
        config = get_config()
        engine = create_async_engine(config.database_url, echo=False)
    return engine


def get_session_factory():
    global async_session_factory
    if async_session_factory is None:
        async_session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return async_session_factory


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db():
    """Create all tables and run lightweight migrations."""
    from backend import models  # noqa: F401 — register models
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Lightweight column migrations for existing tables
    _migrations = [
        "ALTER TABLE runs ADD COLUMN email_sent_at DATETIME",
        "ALTER TABLE runs ADD COLUMN email_sent_by VARCHAR(255)",
    ]
    async with get_engine().begin() as conn:
        for sql in _migrations:
            try:
                await conn.execute(__import__("sqlalchemy").text(sql))
            except Exception:
                pass  # Column already exists
