from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.api_env == "test" and settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, future=True, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def verify_runtime_database() -> None:
    if settings.api_env == "test":
        return
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = set(Base.metadata.tables.keys())
    missing_tables = sorted(required_tables - existing_tables)
    if missing_tables:
        raise RuntimeError(f"Application schema is incomplete in the configured PostgreSQL database. Missing tables: {', '.join(missing_tables)}")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
