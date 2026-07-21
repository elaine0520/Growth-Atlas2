"""Authenticated V2 Decision Episode CRUD and preparation endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.auth import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.models.decision_episode_v2 import DecisionEpisode
from app.models.decision_report_draft_v2 import DecisionReportDraft
from app.schemas.v2_domain import (
    DecisionEpisodeCreate,
    DecisionEpisodeConfirm,
    DecisionEpisodeListItem,
    DecisionEpisodeUpdate,
)
from app.services.decision_episode_service import (
    create_decision_episode,
    delete_decision_episode,
    get_decision_episode,
    list_decision_episodes,
    mark_decision_episode_ready,
    update_decision_episode,
)
from app.services.decision_draft_service import (
    confirm_user_decision,
    generate_decision_draft,
    get_decision_draft,
    get_latest_ready_draft,
)

router = APIRouter(prefix="/decision-episodes")


@router.post(
    "/{episode_id}/drafts/generate",
    response_model=DecisionReportDraft,
    status_code=status.HTTP_201_CREATED,
)
async def generate_episode_draft(
    episode_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionReportDraft:
    """Generate and persist a reviewable draft, never a final decision."""
    return await generate_decision_draft(settings, user, episode_id)


@router.get("/{episode_id}/drafts/latest/ready", response_model=DecisionReportDraft)
async def read_latest_ready_episode_draft(
    episode_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionReportDraft:
    return await get_latest_ready_draft(settings, user, episode_id)


@router.get("/{episode_id}/drafts/{draft_id}", response_model=DecisionReportDraft)
async def read_episode_draft(
    episode_id: UUID,
    draft_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionReportDraft:
    return await get_decision_draft(settings, user, episode_id, draft_id)


@router.post("/{episode_id}/confirm", response_model=DecisionEpisode)
async def confirm_episode(
    episode_id: UUID,
    payload: DecisionEpisodeConfirm,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionEpisode:
    return await confirm_user_decision(settings, user, episode_id, payload)


@router.post("", response_model=DecisionEpisode, status_code=status.HTTP_201_CREATED)
async def create_episode(
    payload: DecisionEpisodeCreate,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionEpisode:
    return await create_decision_episode(settings, user, payload)


@router.get("", response_model=list[DecisionEpisodeListItem])
async def list_episodes(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[DecisionEpisodeListItem]:
    return await list_decision_episodes(settings, user)


@router.get("/{episode_id}", response_model=DecisionEpisode)
async def read_episode(
    episode_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionEpisode:
    return await get_decision_episode(settings, user, episode_id)


@router.patch("/{episode_id}", response_model=DecisionEpisode)
async def update_episode(
    episode_id: UUID,
    payload: DecisionEpisodeUpdate,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionEpisode:
    return await update_decision_episode(settings, user, episode_id, payload)


@router.post("/{episode_id}/ready", response_model=DecisionEpisode)
async def prepare_episode_for_analysis(
    episode_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionEpisode:
    return await mark_decision_episode_ready(settings, user, episode_id)


@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    await delete_decision_episode(settings, user, episode_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
