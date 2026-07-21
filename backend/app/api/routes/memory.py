"""Authenticated Memory Candidate review and Decision Memory management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.auth import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.models.decision_memory_v2 import DecisionMemory, MemoryCandidate
from app.schemas.v2_domain import (
    DecisionMemoryManage,
    FeedbackMemoryCandidateCreate,
    MemoryCandidateConfirm,
    MemoryCandidateReject,
)
from app.services.memory_service import (
    confirm_memory_candidate,
    create_memory_candidate,
    delete_decision_memory,
    list_decision_memories,
    list_memory_candidates,
    manage_decision_memory,
    reject_memory_candidate,
)

router = APIRouter(prefix="/memory")


@router.get("", response_model=list[DecisionMemory])
async def read_memories(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[DecisionMemory]:
    return await list_decision_memories(settings, user)


@router.get("/candidates", response_model=list[MemoryCandidate])
async def read_memory_candidates(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[MemoryCandidate]:
    return await list_memory_candidates(settings, user)


@router.post("/candidates", response_model=MemoryCandidate, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: FeedbackMemoryCandidateCreate,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> MemoryCandidate:
    return await create_memory_candidate(settings, user, payload)


@router.post("/candidates/{candidate_id}/confirm", response_model=DecisionMemory)
async def confirm_candidate(
    candidate_id: UUID,
    payload: MemoryCandidateConfirm,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionMemory:
    return await confirm_memory_candidate(settings, user, candidate_id, payload)


@router.post("/candidates/{candidate_id}/reject", response_model=MemoryCandidate)
async def reject_candidate(
    candidate_id: UUID,
    payload: MemoryCandidateReject,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> MemoryCandidate:
    return await reject_memory_candidate(settings, user, candidate_id, payload)


@router.patch("/{memory_id}", response_model=DecisionMemory)
async def manage_memory(
    memory_id: UUID,
    payload: DecisionMemoryManage,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DecisionMemory:
    return await manage_decision_memory(settings, user, memory_id, payload)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    await delete_decision_memory(settings, user, memory_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
