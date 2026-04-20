from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.orm import Session


class BaseRepository:
    def __init__(self, model: type) -> None:
        self.model = model

    def get(self, db: Session, entity_id: int) -> Any | None:
        stmt = select(self.model).where(self.model.id == entity_id, self.model.is_deleted.is_(False))
        return db.scalar(stmt)

    def list(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        search_fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Any], int]:
        stmt: Select[Any] = select(self.model).where(self.model.is_deleted.is_(False))

        if filters:
            for field, value in filters.items():
                if value in (None, "", []):
                    continue
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        if search and search_fields:
            clauses = [getattr(self.model, field).ilike(f"%{search}%") for field in search_fields if hasattr(self.model, field)]
            if clauses:
                stmt = stmt.where(or_(*clauses))

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        if sort_by and hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            stmt = stmt.order_by(desc(sort_column) if sort_order == "desc" else asc(sort_column))
        else:
            stmt = stmt.order_by(desc(self.model.updated_at))

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt).all()), total

    def create(self, db: Session, payload: dict[str, Any]) -> Any:
        entity = self.model(**payload)
        db.add(entity)
        db.flush()
        db.refresh(entity)
        return entity

    def update(self, db: Session, entity: Any, payload: dict[str, Any]) -> Any:
        for key, value in payload.items():
            setattr(entity, key, value)
        db.add(entity)
        db.flush()
        db.refresh(entity)
        return entity

    def soft_delete(self, db: Session, entity: Any, *, actor_name: str | None = None) -> Any:
        entity.is_deleted = True
        entity.deleted_at = datetime.now(UTC)
        if actor_name is not None and hasattr(entity, "updated_by"):
            entity.updated_by = actor_name
        db.add(entity)
        db.flush()
        return entity
