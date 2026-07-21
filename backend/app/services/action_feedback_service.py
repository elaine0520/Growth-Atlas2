"""User-owned action execution and feedback persistence for one Decision Episode."""

from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.models.action_plan_v2 import ActionItemV2, ActionPlanV2
from app.models.feedback_v2 import FeedbackV2
from app.schemas.v2_domain import (
    ActionItemCompletion,
    EpisodeActionPlanCreate,
    EpisodeFeedbackSubmit,
)


def _headers(settings: Settings, user: CurrentUser) -> dict[str, str]:
    return {
        "apikey": settings.supabase_anon_key or "",
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json",
    }


def _action_item(row: dict[str, Any]) -> ActionItemV2:
    return ActionItemV2(
        id=row["id"],
        description=row["description"],
        sequence=row["sequence"],
        due_at=row.get("due_at"),
        status=row["status"],
        completion_note=row.get("completion_note"),
        completed_at=row.get("completed_at"),
    )


def _action_plan(row: dict[str, Any], items: list[ActionItemV2]) -> ActionPlanV2:
    return ActionPlanV2(
        id=row["id"],
        user_id=row["user_id"],
        schema_version=row.get("schema_version", "2.0"),
        decision_episode_id=row["decision_episode_id"],
        source_report_draft_id=row.get("source_report_draft_id"),
        status=row["status"],
        objective=row["objective"],
        actions=items,
        success_criteria=row.get("success_criteria"),
        key_assumptions=row.get("key_assumptions", []),
        major_obstacles=row.get("major_obstacles", []),
        fallback_plan=row.get("fallback_plan"),
        review_at=row.get("review_at"),
        confirmed_at=row.get("confirmed_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def _load_items(
    settings: Settings,
    user: CurrentUser,
    action_plan_id: UUID,
) -> list[ActionItemV2]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/action_items",
            params={
                "action_plan_id": f"eq.{action_plan_id}",
                "user_id": f"eq.{user.id}",
                "select": "*",
                "order": "sequence.asc",
            },
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to load action items")
    return [_action_item(row) for row in response.json()]


async def get_action_plan(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
) -> ActionPlanV2:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/action_plans",
            params={
                "decision_episode_id": f"eq.{episode_id}",
                "user_id": f"eq.{user.id}",
                "select": "*",
                "order": "created_at.desc",
                "limit": "1",
            },
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to load action plan")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Action plan not found")
    items = await _load_items(settings, user, UUID(rows[0]["id"]))
    return _action_plan(rows[0], items)


async def create_action_plan(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
    payload: EpisodeActionPlanCreate,
) -> ActionPlanV2:
    body = {
        "p_episode_id": str(episode_id),
        "p_objective": payload.objective,
        "p_actions": payload.actions,
        "p_success_criteria": payload.success_criteria,
        "p_major_obstacles": payload.major_obstacles,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/create_episode_action_plan",
            headers=_headers(settings, user),
            json=body,
        )
    if response.status_code not in {200, 201} or not response.json():
        code = 409 if response.status_code in {400, 404, 409} else 502
        raise HTTPException(status_code=code, detail="Unable to create action plan")
    row = response.json()[0]
    items = await _load_items(settings, user, UUID(row["id"]))
    return _action_plan(row, items)


async def complete_action_item(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
    action_plan_id: UUID,
    action_item_id: UUID,
    payload: ActionItemCompletion,
) -> ActionItemV2:
    body = {
        "p_episode_id": str(episode_id),
        "p_action_plan_id": str(action_plan_id),
        "p_action_item_id": str(action_item_id),
        "p_completed": payload.completed,
        "p_completion_note": payload.completion_note,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/complete_action_item",
            headers=_headers(settings, user),
            json=body,
        )
    if response.status_code not in {200, 201} or not response.json():
        code = 409 if response.status_code in {400, 404, 409} else 502
        raise HTTPException(status_code=code, detail="Unable to update action item")
    return _action_item(response.json()[0])


async def submit_feedback(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
    payload: EpisodeFeedbackSubmit,
) -> FeedbackV2:
    body = {
        "p_episode_id": str(episode_id),
        "p_action_plan_id": str(payload.action_plan_id),
        "p_actual_actions": payload.actual_actions,
        "p_actual_outcome": payload.actual_outcome,
        "p_expected_vs_actual": payload.expected_vs_actual,
        "p_lessons_learned": payload.lessons_learned,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/submit_episode_feedback",
            headers=_headers(settings, user),
            json=body,
        )
    if response.status_code not in {200, 201} or not response.json():
        code = 409 if response.status_code in {400, 404, 409} else 502
        raise HTTPException(status_code=code, detail="Unable to submit feedback")
    return FeedbackV2.model_validate(response.json()[0])


async def get_latest_feedback(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
) -> FeedbackV2:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/feedback_entries",
            params={
                "decision_episode_id": f"eq.{episode_id}",
                "user_id": f"eq.{user.id}",
                "select": "*",
                "order": "created_at.desc",
                "limit": "1",
            },
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to load feedback")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return FeedbackV2.model_validate(rows[0])
