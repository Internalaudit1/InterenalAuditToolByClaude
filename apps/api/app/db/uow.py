from __future__ import annotations

from sqlalchemy.orm import Session


class UnitOfWork:
    def __init__(self, db: Session) -> None:
        self.db = db

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:
        if exc_type is not None:
            self.db.rollback()
            return
        self.db.commit()

