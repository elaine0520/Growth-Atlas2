import asyncio
from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.models.v2_common import DecisionMemoryStatus, MemoryType
from app.schemas.v2_domain import (
    DecisionMemoryManage,
    FeedbackMemoryCandidateCreate,
    MemoryCandidateConfirm,
)
from app.services import memory_service


USER_ID = UUID("11111111-1111-1111-1111-111111111111")
EPISODE_ID = UUID("22222222-2222-2222-2222-222222222222")
FEEDBACK_ID = UUID("33333333-3333-3333-3333-333333333333")
CANDIDATE_ID = UUID("44444444-4444-4444-4444-444444444444")
MEMORY_ID = UUID("55555555-5555-5555-5555-555555555555")
NOW = datetime.now(timezone.utc).isoformat()
SETTINGS = Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon")
USER = CurrentUser(id=USER_ID, access_token="token")
EVIDENCE = [
    {"source_type": "feedback", "source_id": str(FEEDBACK_ID), "note": "User-confirmed feedback"},
    {"source_type": "decision_episode", "source_id": str(EPISODE_ID), "note": "Source decision episode"},
]


def _candidate_row(status: str = "suggested") -> dict[str, object]:
    return {
        "id": str(CANDIDATE_ID), "user_id": str(USER_ID), "schema_version": "2.0",
        "decision_episode_id": str(EPISODE_ID), "feedback_id": str(FEEDBACK_ID),
        "candidate_type": "confirmed_lesson", "proposed_content": "提前说明约束",
        "rationale": "这次谈判验证有效", "evidence": EVIDENCE,
        "applicable_domains": ["career"], "confidence": 0.5, "status": status,
        "proposed_expires_at": None, "reviewed_at": NOW if status == "confirmed" else None,
        "created_at": NOW, "updated_at": NOW,
    }


def _memory_row(status: str = "active") -> dict[str, object]:
    return {
        "id": str(MEMORY_ID), "user_id": str(USER_ID), "schema_version": "2.0",
        "source_candidate_id": str(CANDIDATE_ID), "memory_type": "confirmed_lesson",
        "content": "提前说明现实约束有助于谈判", "applicable_domains": ["career"],
        "evidence": EVIDENCE, "confidence": 0.75, "status": status,
        "effective_from": NOW, "effective_until": None, "review_after": None,
        "confirmed_at": NOW, "last_used_at": None, "usage_count": 0,
        "supersedes_memory_id": None, "created_at": NOW, "updated_at": NOW,
    }


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


class FakeClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    async def __aenter__(self) -> "FakeClient": return self
    async def __aexit__(self, *args: object) -> None: return None

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    async def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)

    async def patch(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append(("PATCH", url, kwargs))
        return self.responses.pop(0)


def test_candidate_is_created_only_from_feedback_source(monkeypatch) -> None:
    client = FakeClient([FakeResponse(200, [_candidate_row()])])
    monkeypatch.setattr(memory_service.httpx, "AsyncClient", lambda **_: client)
    payload = FeedbackMemoryCandidateCreate(
        feedback_id=FEEDBACK_ID, candidate_type=MemoryType.CONFIRMED_LESSON,
        proposed_content="提前说明约束", rationale="这次谈判验证有效",
        applicable_domains=["career"],
    )

    candidate = asyncio.run(memory_service.create_memory_candidate(SETTINGS, USER, payload))

    assert candidate.feedback_id == FEEDBACK_ID
    assert candidate.evidence[0].source_id == FEEDBACK_ID
    assert client.calls[0][1].endswith("/rpc/create_feedback_memory_candidate")
    assert client.calls[0][2]["json"]["p_feedback_id"] == str(FEEDBACK_ID)


def test_memory_requires_explicit_true_confirmation() -> None:
    with pytest.raises(ValidationError):
        MemoryCandidateConfirm(
            content="经验", applicable_domains=[], user_confirmed=False,  # type: ignore[arg-type]
        )


def test_user_confirmation_creates_sourced_decision_memory(monkeypatch) -> None:
    client = FakeClient([FakeResponse(200, [_memory_row()])])
    monkeypatch.setattr(memory_service.httpx, "AsyncClient", lambda **_: client)
    payload = MemoryCandidateConfirm(
        content="提前说明现实约束有助于谈判",
        applicable_domains=["career"], user_confirmed=True,
    )

    memory = asyncio.run(memory_service.confirm_memory_candidate(
        SETTINGS, USER, CANDIDATE_ID, payload,
    ))

    assert memory.source_candidate_id == CANDIDATE_ID
    assert memory.evidence[0].source_id == FEEDBACK_ID
    assert client.calls[0][2]["json"]["p_user_confirmed"] is True
    assert client.calls[0][1].endswith("/rpc/confirm_memory_candidate")


def test_memory_can_be_disabled_and_soft_deleted(monkeypatch) -> None:
    client = FakeClient([
        FakeResponse(200, [_memory_row()]),
        FakeResponse(200, [_memory_row("disabled")]),
        FakeResponse(200, [_memory_row("disabled")]),
        FakeResponse(200, [_memory_row("deleted")]),
    ])
    monkeypatch.setattr(memory_service.httpx, "AsyncClient", lambda **_: client)

    disabled = asyncio.run(memory_service.manage_decision_memory(
        SETTINGS, USER, MEMORY_ID, DecisionMemoryManage(target_status="disabled"),
    ))
    asyncio.run(memory_service.delete_decision_memory(SETTINGS, USER, MEMORY_ID))

    assert disabled.status == DecisionMemoryStatus.DISABLED
    assert client.calls[1][2]["json"]["p_target_status"] == "disabled"
    assert client.calls[3][2]["json"]["p_target_status"] == "deleted"
