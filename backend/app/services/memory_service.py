"""Explicit-review Decision Memory persistence; no automatic long-term writes."""

from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.models.decision_memory_v2 import DecisionMemory, MemoryCandidate
from app.models.v2_common import (
    DECISION_MEMORY_TRANSITIONS,
    DecisionMemoryStatus,
    can_transition,
)
from app.schemas.v2_domain import (
    DecisionMemoryManage,
    FeedbackMemoryCandidateCreate,
    MemoryCandidateConfirm,
    MemoryCandidateReject,
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


def _candidate(row: dict[str, Any]) -> MemoryCandidate:
    return MemoryCandidate.model_validate(row)


def _memory(row: dict[str, Any]) -> DecisionMemory:
    return DecisionMemory.model_validate(row)


async def create_memory_candidate(
    settings: Settings,
    user: CurrentUser,
    payload: FeedbackMemoryCandidateCreate,
) -> MemoryCandidate:
    body = {
        "p_feedback_id": str(payload.feedback_id),
        "p_candidate_type": payload.candidate_type.value,
        "p_proposed_content": payload.proposed_content,
        "p_rationale": payload.rationale,
        "p_applicable_domains": payload.applicable_domains,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/create_feedback_memory_candidate",
            headers=_headers(settings, user),
            json=body,
        )
    if response.status_code not in {200, 201} or not response.json():
        code = 409 if response.status_code in {400, 404, 409} else 502
        raise HTTPException(status_code=code, detail="Unable to create memory candidate")
    return _candidate(response.json()[0])


async def list_memory_candidates(
    settings: Settings,
    user: CurrentUser,
) -> list[MemoryCandidate]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/memory_candidates",
            params={
                "user_id": f"eq.{user.id}",
                "status": "in.(suggested,edited)",
                "select": "*",
                "order": "created_at.desc",
            },
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to load memory candidates")
    return [_candidate(row) for row in response.json()]


async def confirm_memory_candidate(
    settings: Settings,
    user: CurrentUser,
    candidate_id: UUID,
    payload: MemoryCandidateConfirm,
) -> DecisionMemory:
    body = {
        "p_candidate_id": str(candidate_id),
        "p_content": payload.content,
        "p_applicable_domains": payload.applicable_domains,
        "p_user_confirmed": payload.user_confirmed,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/confirm_memory_candidate",
            headers=_headers(settings, user),
            json=body,
        )
    if response.status_code not in {200, 201} or not response.json():
        code = 409 if response.status_code in {400, 404, 409} else 502
        raise HTTPException(status_code=code, detail="Unable to confirm memory candidate")
    return _memory(response.json()[0])


async def reject_memory_candidate(
    settings: Settings,
    user: CurrentUser,
    candidate_id: UUID,
    payload: MemoryCandidateReject,
) -> MemoryCandidate:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/reject_memory_candidate",
            headers=_headers(settings, user),
            json={"p_candidate_id": str(candidate_id)},
        )
    if response.status_code != 200 or not response.json():
        raise HTTPException(status_code=409, detail="Memory candidate cannot be rejected")
    return _candidate(response.json()[0])


async def list_decision_memories(
    settings: Settings,
    user: CurrentUser,
) -> list[DecisionMemory]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_memories",
            params={
                "user_id": f"eq.{user.id}",
                "status": "neq.deleted",
                "select": "*",
                "order": "updated_at.desc",
            },
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to load decision memories")
    return [_memory(row) for row in response.json()]


async def get_decision_memory(
    settings: Settings,
    user: CurrentUser,
    memory_id: UUID,
) -> DecisionMemory:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_memories",
            params={"id": f"eq.{memory_id}", "user_id": f"eq.{user.id}", "select": "*"},
            headers=_headers(settings, user),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to load decision memory")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Decision memory not found")
    return _memory(rows[0])


async def manage_decision_memory(
    settings: Settings,
    user: CurrentUser,
    memory_id: UUID,
    payload: DecisionMemoryManage,
) -> DecisionMemory:
    current = await get_decision_memory(settings, user, memory_id)
    target = DecisionMemoryStatus(payload.target_status)
    if current.status == target:
        return current
    if not can_transition(current.status, target, DECISION_MEMORY_TRANSITIONS):
        raise HTTPException(status_code=409, detail="Invalid decision memory transition")
    return await _update_memory_status(settings, user, memory_id, current.status, target)


async def delete_decision_memory(
    settings: Settings,
    user: CurrentUser,
    memory_id: UUID,
) -> None:
    current = await get_decision_memory(settings, user, memory_id)
    if current.status == DecisionMemoryStatus.DELETED:
        return
    if not can_transition(
        current.status, DecisionMemoryStatus.DELETED, DECISION_MEMORY_TRANSITIONS
    ):
        raise HTTPException(status_code=409, detail="Decision memory cannot be deleted")
    await _update_memory_status(
        settings, user, memory_id, current.status, DecisionMemoryStatus.DELETED
    )


async def _update_memory_status(
    settings: Settings,
    user: CurrentUser,
    memory_id: UUID,
    current_status: DecisionMemoryStatus,
    target_status: DecisionMemoryStatus,
) -> DecisionMemory:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/set_decision_memory_status",
            headers=_headers(settings, user),
            json={"p_memory_id": str(memory_id), "p_target_status": target_status.value},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Unable to update decision memory")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=409, detail="Decision memory changed; reload and retry")
    return _memory(rows[0])
