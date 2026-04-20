from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.core.exceptions import NotFoundException
from app.models.support import Attachment, KnowledgeLibraryItem
from app.repositories.base import BaseRepository
from app.schemas.common import BlockedDeleteItem, BulkDeleteResponse, ListQuery, PaginationMeta, PaginatedResponse
from app.schemas.library import KnowledgeLibraryItemCreate, KnowledgeLibraryItemUpdate
from app.services.activity_log import activity_log_service
from app.utils.serialization import model_to_dict


class LibraryService:
    repo = BaseRepository(KnowledgeLibraryItem)
    attachment_repo = BaseRepository(Attachment)

    def list(self, db: Session, query: ListQuery) -> PaginatedResponse[KnowledgeLibraryItem]:
        items, total = self.repo.list(
            db,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            search_fields=["title", "description", "category", "item_type"],
            filters=query.filters,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        return PaginatedResponse(items=items, meta=PaginationMeta(page=query.page, page_size=query.page_size, total=total))

    def create(self, db: Session, payload: KnowledgeLibraryItemCreate, actor_name: str, actor_id: int | None) -> KnowledgeLibraryItem:
        data = payload.model_dump()
        data["created_by"] = actor_name
        data["updated_by"] = actor_name
        item = self.repo.create(db, data)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="knowledge_library",
            entity_type="knowledge_library_item",
            entity_id=str(item.id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(item),
        )
        return item

    def update(self, db: Session, item_id: int, payload: KnowledgeLibraryItemUpdate, actor_name: str, actor_id: int | None) -> KnowledgeLibraryItem:
        item = self.repo.get(db, item_id)
        if not item:
            raise NotFoundException("Knowledge library item not found.")
        before = model_to_dict(item)
        data = payload.model_dump(exclude_none=True)
        data["updated_by"] = actor_name
        item = self.repo.update(db, item, data)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="knowledge_library",
            entity_type="knowledge_library_item",
            entity_id=str(item.id),
            action_type=ActivityAction.UPDATE.value,
            old_values=before,
            new_values=model_to_dict(item),
        )
        return item

    def delete(self, db: Session, item_id: int, actor_name: str, actor_id: int | None) -> None:
        item = self.repo.get(db, item_id)
        if not item:
            raise NotFoundException("Knowledge library item not found.")
        before = model_to_dict(item)
        if item.attachment_id:
            attachment = self.attachment_repo.get(db, item.attachment_id)
            if attachment:
                self.attachment_repo.soft_delete(db, attachment, actor_name=actor_name)
        self.repo.soft_delete(db, item, actor_name=actor_name)
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="knowledge_library",
            entity_type="knowledge_library_item",
            entity_id=str(item.id),
            action_type=ActivityAction.DELETE.value,
            old_values=before,
            new_values={"is_deleted": True},
        )

    def bulk_delete(self, db: Session, ids: list[int], actor_name: str, actor_id: int | None) -> BulkDeleteResponse:
        deleted_ids: list[int] = []
        blocked: list[BlockedDeleteItem] = []
        for item_id in ids:
            try:
                self.delete(db, item_id, actor_name, actor_id)
                deleted_ids.append(item_id)
            except NotFoundException as exc:
                blocked.append(BlockedDeleteItem(id=item_id, reason=str(exc.detail)))
        response = BulkDeleteResponse(
            deleted_ids=deleted_ids,
            blocked=blocked,
            message=(
                f"Deleted {len(deleted_ids)} record(s)." if deleted_ids and not blocked else
                f"Deleted {len(deleted_ids)} record(s); {len(blocked)} record(s) could not be deleted." if deleted_ids else
                "No records were deleted."
            ),
        )
        activity_log_service.log(
            db,
            actor_user_id=actor_id,
            actor_name=actor_name,
            role=None,
            module="knowledge_library",
            entity_type="knowledge_library_item",
            entity_id="bulk",
            action_type=ActivityAction.DELETE.value,
            new_values=response.model_dump(),
        )
        return response


library_service = LibraryService()
