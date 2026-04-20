from __future__ import annotations

from pydantic import BaseModel

from app.schemas.base import BaseResponse


class KnowledgeLibraryItemBase(BaseModel):
    item_type: str
    title: str
    description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    attachment_id: int | None = None
    approved_for_auditee: bool = True


class KnowledgeLibraryItemCreate(KnowledgeLibraryItemBase):
    pass


class KnowledgeLibraryItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    attachment_id: int | None = None
    approved_for_auditee: bool | None = None


class KnowledgeLibraryItemResponse(BaseResponse, KnowledgeLibraryItemBase):
    pass
