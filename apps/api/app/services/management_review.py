from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import CurrentUser
from app.core.enums import ActivityAction, RoleCode
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.action_plan import ActionPlan
from app.models.support import ManagementReview
from app.repositories.base import BaseRepository
from app.schemas.management_review import ManagementReviewCreate
from app.services.activity_log import activity_log_service
from app.utils.serialization import model_to_dict


class ManagementReviewService:
    review_repo = BaseRepository(ManagementReview)

    def list_for_action_plan(self, db: Session, action_plan_id: int) -> list[ManagementReview]:
        self._ensure_action_plan_exists(db, action_plan_id)
        stmt = (
            select(ManagementReview)
            .options(joinedload(ManagementReview.created_by_user))
            .where(ManagementReview.action_plan_id == action_plan_id, ManagementReview.is_deleted.is_(False))
            .order_by(ManagementReview.created_at.desc())
        )
        return list(db.execute(stmt).unique().scalars().all())

    def create_for_action_plan(self, db: Session, action_plan_id: int, payload: ManagementReviewCreate, current_user: CurrentUser) -> ManagementReview:
        self._ensure_action_plan_exists(db, action_plan_id)
        if RoleCode.MANAGEMENT.value not in current_user.role_codes:
            raise ForbiddenException("Only Management users can create management review notes.")
        review = ManagementReview(
            action_plan_id=action_plan_id,
            review_note=payload.review_note,
            review_decision=payload.review_decision,
            created_by_user_id=current_user.id,
            created_by=current_user.full_name,
            updated_by=current_user.full_name,
        )
        db.add(review)
        db.flush()
        db.refresh(review)
        activity_log_service.log(
            db,
            actor_user_id=current_user.id,
            actor_name=current_user.full_name,
            role=",".join(current_user.role_codes),
            module="management_reviews",
            entity_type="action_plan",
            entity_id=str(action_plan_id),
            action_type=ActivityAction.CREATE.value,
            new_values=model_to_dict(review),
        )
        return review

    def _ensure_action_plan_exists(self, db: Session, action_plan_id: int) -> None:
        exists = db.scalar(select(ActionPlan.id).where(ActionPlan.id == action_plan_id, ActionPlan.is_deleted.is_(False)))
        if not exists:
            raise NotFoundException("Action plan not found.")


management_review_service = ManagementReviewService()
