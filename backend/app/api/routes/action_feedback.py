"""Action Plan execution and Feedback endpoints for a Decision Episode."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.auth import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.models.action_plan_v2 import ActionItemV2, ActionPlanV2
from app.models.feedback_v2 import FeedbackV2
from app.schemas.v2_domain import (
    ActionItemCompletion,
    EpisodeActionPlanCreate,
    EpisodeFeedbackSubmit,
)
from app.services.action_feedback_service import (
    complete_action_item,
    create_action_plan,
    get_action_plan,
    get_latest_feedback,
    submit_feedback,
)

router = APIRouter(prefix="/decision-episodes/{episode_id}")


@router.post("/action-plan", response_model=ActionPlanV2, status_code=status.HTTP_201_CREATED)
async def create_episode_action_plan(
    episode_id: UUID,
    payload: EpisodeActionPlanCreate,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ActionPlanV2:
    return await create_action_plan(settings, user, episode_id, payload)


@router.get("/action-plan", response_model=ActionPlanV2)
async def read_episode_action_plan(
    episode_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ActionPlanV2:
    return await get_action_plan(settings, user, episode_id)


@router.patch("/action-plan/{action_plan_id}/actions/{action_item_id}", response_model=ActionItemV2)
async def update_episode_action_item(
    episode_id: UUID,
    action_plan_id: UUID,
    action_item_id: UUID,
    payload: ActionItemCompletion,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ActionItemV2:
    return await complete_action_item(
        settings, user, episode_id, action_plan_id, action_item_id, payload
    )


@router.post("/feedback", response_model=FeedbackV2, status_code=status.HTTP_201_CREATED)
async def submit_episode_feedback(
    episode_id: UUID,
    payload: EpisodeFeedbackSubmit,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> FeedbackV2:
    return await submit_feedback(settings, user, episode_id, payload)


@router.get("/feedback/latest", response_model=FeedbackV2)
async def read_latest_episode_feedback(
    episode_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> FeedbackV2:
    return await get_latest_feedback(settings, user, episode_id)
