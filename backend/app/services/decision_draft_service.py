"""Persistence workflow for AI-generated Decision Report Drafts."""

from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.models.decision_report_draft_v2 import DecisionReportDraft
from app.models.decision_episode_v2 import DecisionEpisode
from app.models.v2_common import DecisionEpisodeStatus, ReportDraftStatus
from app.schemas.v2_domain import DecisionEpisodeConfirm
from app.services.ai_decision_draft_service import AIDecisionDraftService
from app.services.decision_episode_service import _episode, get_decision_episode
from app.services.decision_context_retrieval import DecisionContextRetrievalService


def _headers(settings: Settings, user: CurrentUser, *, return_row: bool = False) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_anon_key or "",
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json",
    }
    if return_row:
        headers["Prefer"] = "return=representation"
    return headers


def _draft(row: dict[str, Any]) -> DecisionReportDraft:
    return DecisionReportDraft.model_validate(row)


async def _patch_episode(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
    expected_status: DecisionEpisodeStatus,
    body: dict[str, Any],
) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.patch(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_episodes",
            params={
                "id": f"eq.{episode_id}",
                "user_id": f"eq.{user.id}",
                "status": f"eq.{expected_status.value}",
            },
            headers=_headers(settings, user, return_row=True),
            json=body,
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to update decision episode")
    if not response.json():
        raise HTTPException(status_code=409, detail="Decision episode changed; reload and retry")


async def _next_version(settings: Settings, user: CurrentUser, episode_id: UUID) -> int:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_report_drafts",
            params={
                "decision_episode_id": f"eq.{episode_id}",
                "user_id": f"eq.{user.id}",
                "select": "version",
                "order": "version.desc",
                "limit": "1",
            },
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to allocate draft version")
    rows = response.json()
    return int(rows[0]["version"]) + 1 if rows else 1


async def get_decision_draft(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
    draft_id: UUID,
) -> DecisionReportDraft:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_report_drafts",
            params={
                "id": f"eq.{draft_id}",
                "decision_episode_id": f"eq.{episode_id}",
                "user_id": f"eq.{user.id}",
                "select": "*",
            },
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to load decision draft")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Decision draft not found")
    return _draft(rows[0])


async def get_latest_ready_draft(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
) -> DecisionReportDraft:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_report_drafts",
            params={
                "decision_episode_id": f"eq.{episode_id}",
                "user_id": f"eq.{user.id}",
                "status": f"eq.{ReportDraftStatus.READY.value}",
                "select": "*",
                "order": "version.desc",
                "limit": "1",
            },
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to load latest decision draft")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Ready decision draft not found")
    return _draft(rows[0])


async def confirm_user_decision(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
    payload: DecisionEpisodeConfirm,
) -> DecisionEpisode:
    """Atomically preserve the AI draft and commit a separate user decision."""
    body = {
        "p_episode_id": str(episode_id),
        "p_draft_id": str(payload.draft_id),
        "p_final_decision": payload.final_decision,
        "p_decision_rationale": payload.decision_rationale,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/confirm_decision_episode",
            headers=_headers(settings, user),
            json=body,
        )
    if response.status_code not in {200, 201}:
        if response.status_code in {400, 404}:
            raise HTTPException(status_code=409, detail="Decision cannot be confirmed")
        raise HTTPException(status_code=502, detail="Unable to confirm decision")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=409, detail="Decision was not confirmed")
    return _episode(rows[0])


async def generate_decision_draft(
    settings: Settings,
    user: CurrentUser,
    episode_id: UUID,
) -> DecisionReportDraft:
    episode = await get_decision_episode(settings, user, episode_id)
    if episode.status not in {
        DecisionEpisodeStatus.READY_FOR_ANALYSIS,
        DecisionEpisodeStatus.ANALYSIS_FAILED,
        DecisionEpisodeStatus.DRAFT_READY,
    }:
        raise HTTPException(status_code=409, detail="Decision episode is not ready for analysis")

    starting_status = episode.status
    version = await _next_version(settings, user, episode_id)
    await _patch_episode(
        settings,
        user,
        episode_id,
        starting_status,
        {"status": DecisionEpisodeStatus.ANALYZING.value},
    )

    draft_body = {
        "user_id": str(user.id),
        "decision_episode_id": str(episode_id),
        "version": version,
        "status": ReportDraftStatus.GENERATING.value,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_report_drafts",
            headers=_headers(settings, user, return_row=True),
            json=draft_body,
        )
    if response.status_code != 201 or not response.json():
        await _patch_episode(
            settings,
            user,
            episode_id,
            DecisionEpisodeStatus.ANALYZING,
            {"status": DecisionEpisodeStatus.ANALYSIS_FAILED.value},
        )
        raise HTTPException(status_code=502, detail="Unable to create decision draft")
    draft_id = UUID(response.json()[0]["id"])

    try:
        retrieved_context = await DecisionContextRetrievalService().retrieve(
            settings, user, episode
        )
        ai_service = AIDecisionDraftService(settings)
        content, context = await ai_service.generate(episode, retrieved_context)
        completed = content.model_dump(mode="json")
        completed.update(
            {
                "status": ReportDraftStatus.READY.value,
                "model_provider": "kimi",
                "model_name": ai_service.model_name,
                "prompt_version": "decision-draft-v2",
                "context_version": context.version,
                "context_snapshot": context.snapshot,
            }
        )
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.patch(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_report_drafts",
                params={
                    "id": f"eq.{draft_id}",
                    "user_id": f"eq.{user.id}",
                    "status": f"eq.{ReportDraftStatus.GENERATING.value}",
                },
                headers=_headers(settings, user, return_row=True),
                json=completed,
            )
        if response.status_code != 200 or not response.json():
            raise RuntimeError("Unable to persist generated decision draft")
        await _patch_episode(
            settings,
            user,
            episode_id,
            DecisionEpisodeStatus.ANALYZING,
            {
                "status": DecisionEpisodeStatus.DRAFT_READY.value,
                "context_snapshot": context.snapshot,
            },
        )
        return _draft(response.json()[0])
    except Exception as exc:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_report_drafts",
                params={"id": f"eq.{draft_id}", "user_id": f"eq.{user.id}"},
                headers=_headers(settings, user),
                json={"status": ReportDraftStatus.GENERATION_FAILED.value},
            )
        await _patch_episode(
            settings,
            user,
            episode_id,
            DecisionEpisodeStatus.ANALYZING,
            {"status": DecisionEpisodeStatus.ANALYSIS_FAILED.value},
        )
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=503, detail="AI draft generation failed") from exc
