"""Persistence and lifecycle operations for V2 Decision Episodes."""

from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.models.decision_episode_v2 import DecisionEpisode
from app.models.v2_common import (
    DECISION_EPISODE_TRANSITIONS,
    DecisionEpisodeStatus,
    can_transition,
)
from app.schemas.v2_domain import (
    DecisionEpisodeCreate,
    DecisionEpisodeListItem,
    DecisionEpisodeUpdate,
)


def _headers(settings: Settings, user: CurrentUser, *, return_row: bool = False) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_anon_key or "",
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json",
    }
    if return_row:
        headers["Prefer"] = "return=representation"
    return headers


def _episode(row: dict[str, Any]) -> DecisionEpisode:
    return DecisionEpisode(
        id=row["id"],
        user_id=row["user_id"],
        schema_version=row.get("schema_version", "2.0"),
        title=row["title"],
        decision_question=row["decision_question"],
        domain=row.get("domain"),
        importance=row.get("importance"),
        background=row.get("background"),
        context_snapshot=row.get("context_snapshot"),
        goal=row.get("goal"),
        values=row.get("values_data", []),
        facts=row.get("facts", []),
        assumptions=row.get("assumptions", []),
        unknowns=row.get("unknowns", []),
        constraints=row.get("constraints_data", []),
        options=row.get("options", []),
        final_decision=row.get("final_decision"),
        decision_rationale=row.get("decision_rationale"),
        evidence=row.get("evidence", []),
        status=row["status"],
        profile_version_id=row.get("profile_version_id"),
        profile_id=None,
        profile_version=None,
        confirmed_from_draft_id=row.get("confirmed_from_draft_id"),
        committed_at=row.get("committed_at"),
        closed_at=row.get("closed_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _update_payload(payload: DecisionEpisodeUpdate) -> dict[str, Any]:
    body = payload.model_dump(mode="json", exclude_unset=True)
    body.pop("schema_version", None)
    if "values" in body:
        body["values_data"] = body.pop("values")
    if "constraints" in body:
        body["constraints_data"] = body.pop("constraints")
    return body


async def create_decision_episode(
    settings: Settings,
    user: CurrentUser,
    payload: DecisionEpisodeCreate,
) -> DecisionEpisode:
    body = payload.model_dump(mode="json", exclude={"schema_version"})
    body.update({"user_id": str(user.id), "status": DecisionEpisodeStatus.CAPTURING.value})
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_episodes",
            headers=_headers(settings, user, return_row=True),
            json=body,
        )
    if response.status_code != 201 or not response.json():
        raise HTTPException(status_code=502, detail="Unable to create decision episode")
    return _episode(response.json()[0])


async def get_decision_episode(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
) -> DecisionEpisode:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_episodes",
            params={"id": f"eq.{episode_id}", "user_id": f"eq.{user.id}", "select": "*"},
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to load decision episode")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Decision episode not found")
    return _episode(rows[0])


async def list_decision_episodes(
    settings: Settings,
    user: CurrentUser,
) -> list[DecisionEpisodeListItem]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_episodes",
            params={
                "user_id": f"eq.{user.id}",
                "select": "id,title,decision_question,domain,status,created_at,updated_at",
                "order": "updated_at.desc,id.desc",
                "limit": "100",
            },
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to list decision episodes")
    return [DecisionEpisodeListItem.model_validate(row) for row in response.json()]


async def update_decision_episode(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
    payload: DecisionEpisodeUpdate,
) -> DecisionEpisode:
    current = await get_decision_episode(settings, user, episode_id)
    if current.status not in {
        DecisionEpisodeStatus.CAPTURING,
        DecisionEpisodeStatus.READY_FOR_ANALYSIS,
    }:
        raise HTTPException(status_code=409, detail="Decision episode can no longer be edited")
    body = _update_payload(payload)
    if not body:
        return current
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.patch(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_episodes",
            params={
                "id": f"eq.{episode_id}",
                "user_id": f"eq.{user.id}",
                "status": f"eq.{current.status.value}",
            },
            headers=_headers(settings, user, return_row=True),
            json=body,
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to update decision episode")
    if not response.json():
        raise HTTPException(status_code=409, detail="Decision episode changed; reload and retry")
    return _episode(response.json()[0])


async def mark_decision_episode_ready(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
) -> DecisionEpisode:
    current = await get_decision_episode(settings, user, episode_id)
    if current.status == DecisionEpisodeStatus.READY_FOR_ANALYSIS:
        return current
    if not current.background or not current.background.strip():
        raise HTTPException(status_code=409, detail="Add decision background before analysis")
    if not current.goal or not current.goal.strip():
        raise HTTPException(status_code=409, detail="Add a decision goal before analysis")
    if not current.facts:
        raise HTTPException(status_code=409, detail="Add at least one known fact before analysis")
    if not current.unknowns:
        raise HTTPException(status_code=409, detail="Add at least one unknown before analysis")
    if len(current.options) < 2:
        raise HTTPException(status_code=409, detail="Add at least two options before analysis")
    if not can_transition(
        current.status,
        DecisionEpisodeStatus.READY_FOR_ANALYSIS,
        DECISION_EPISODE_TRANSITIONS,
    ):
        raise HTTPException(status_code=409, detail="Invalid decision episode transition")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.patch(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_episodes",
            params={
                "id": f"eq.{episode_id}",
                "user_id": f"eq.{user.id}",
                "status": f"eq.{current.status.value}",
            },
            headers=_headers(settings, user, return_row=True),
            json={"status": DecisionEpisodeStatus.READY_FOR_ANALYSIS.value},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to prepare decision episode")
    if not response.json():
        raise HTTPException(status_code=409, detail="Decision episode changed; reload and retry")
    return _episode(response.json()[0])


async def delete_decision_episode(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
) -> None:
    current = await get_decision_episode(settings, user, episode_id)
    if current.status not in {
        DecisionEpisodeStatus.CAPTURING,
        DecisionEpisodeStatus.CANCELLED,
        DecisionEpisodeStatus.ABANDONED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only unfinished decision episodes can be deleted",
        )
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.delete(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_episodes",
            params={"id": f"eq.{episode_id}", "user_id": f"eq.{user.id}"},
            headers=_headers(settings, user),
        )
    if response.status_code != 204:
        raise HTTPException(status_code=502, detail="Unable to delete decision episode")
