import asyncio
from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.models.v2_common import DecisionEpisodeStatus
from app.schemas.v2_domain import DecisionEpisodeCreate, DecisionEpisodeUpdate
from app.services import decision_episode_service


USER_ID = UUID("11111111-1111-1111-1111-111111111111")
EPISODE_ID = UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime.now(timezone.utc).isoformat()


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": str(EPISODE_ID),
        "user_id": str(USER_ID),
        "schema_version": "2.0",
        "title": "是否接受实习",
        "decision_question": "我是否应该接受这个实习机会？",
        "domain": "career",
        "importance": 4,
        "background": None,
        "context_snapshot": None,
        "goal": None,
        "values_data": [],
        "facts": [],
        "assumptions": [],
        "unknowns": [],
        "constraints_data": [],
        "options": [],
        "final_decision": None,
        "decision_rationale": None,
        "evidence": [],
        "status": "capturing",
        "profile_version_id": None,
        "committed_at": None,
        "closed_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(overrides)
    return row


class FakeResponse:
    def __init__(self, status_code: int, payload: object = None) -> None:
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

    async def delete(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append(("DELETE", url, kwargs))
        return self.responses.pop(0)


SETTINGS = Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon")
USER = CurrentUser(id=USER_ID, access_token="token")


def test_create_then_reload_episode_is_user_scoped(monkeypatch) -> None:
    client = FakeClient([FakeResponse(201, [_row()]), FakeResponse(200, [_row()])])
    monkeypatch.setattr(decision_episode_service.httpx, "AsyncClient", lambda **_: client)
    created = asyncio.run(decision_episode_service.create_decision_episode(
        SETTINGS, USER, DecisionEpisodeCreate(
            title="是否接受实习", decision_question="我是否应该接受这个实习机会？",
            domain="career", importance=4,
        )
    ))
    reloaded = asyncio.run(decision_episode_service.get_decision_episode(
        SETTINGS, USER, created.id,
    ))

    assert created.id == reloaded.id == EPISODE_ID
    assert client.calls[0][2]["json"]["user_id"] == str(USER_ID)
    assert client.calls[1][2]["params"]["user_id"] == f"eq.{USER_ID}"


def test_background_can_be_saved_and_episode_marked_ready(monkeypatch) -> None:
    background = "实习每周占用三天，目前同时准备考试。"
    complete = {
        "background": background,
        "goal": "在不影响考试的前提下获得行业经验",
        "facts": ["实习每周占用三天"],
        "unknowns": ["能否调整出勤时间"],
        "options": ["接受实习", "拒绝实习"],
    }
    client = FakeClient([
        FakeResponse(200, [_row()]),
        FakeResponse(200, [_row(**complete)]),
        FakeResponse(200, [_row(**complete)]),
        FakeResponse(200, [_row(**complete, status="ready_for_analysis")]),
    ])
    monkeypatch.setattr(decision_episode_service.httpx, "AsyncClient", lambda **_: client)

    saved = asyncio.run(decision_episode_service.update_decision_episode(
        SETTINGS, USER, EPISODE_ID,
        DecisionEpisodeUpdate(
            background=background,
            goal="在不影响考试的前提下获得行业经验",
            facts=["实习每周占用三天"],
            unknowns=["能否调整出勤时间"],
            options=["接受实习", "拒绝实习"],
        ),
    ))
    ready = asyncio.run(decision_episode_service.mark_decision_episode_ready(
        SETTINGS, USER, EPISODE_ID,
    ))

    assert saved.background == background
    assert ready.status == DecisionEpisodeStatus.READY_FOR_ANALYSIS
    assert client.calls[-1][2]["json"] == {"status": "ready_for_analysis"}


def test_episode_cannot_be_ready_without_background(monkeypatch) -> None:
    client = FakeClient([FakeResponse(200, [_row()])])
    monkeypatch.setattr(decision_episode_service.httpx, "AsyncClient", lambda **_: client)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(decision_episode_service.mark_decision_episode_ready(
            SETTINGS, USER, EPISODE_ID,
        ))
    assert caught.value.status_code == 409


@pytest.mark.parametrize(
    ("overrides", "detail"),
    [
        ({"goal": None}, "Add a decision goal before analysis"),
        ({"facts": []}, "Add at least one known fact before analysis"),
        ({"unknowns": []}, "Add at least one unknown before analysis"),
        ({"options": ["接受实习"]}, "Add at least two options before analysis"),
    ],
)
def test_episode_requires_decision_foundation_before_analysis(
    monkeypatch, overrides: dict[str, object], detail: str,
) -> None:
    complete = {
        "background": "实习每周占用三天。",
        "goal": "获得行业经验",
        "facts": ["每周占用三天"],
        "unknowns": ["能否调整出勤时间"],
        "options": ["接受实习", "拒绝实习"],
    }
    complete.update(overrides)
    client = FakeClient([FakeResponse(200, [_row(**complete)])])
    monkeypatch.setattr(decision_episode_service.httpx, "AsyncClient", lambda **_: client)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(decision_episode_service.mark_decision_episode_ready(
            SETTINGS, USER, EPISODE_ID,
        ))

    assert caught.value.status_code == 409
    assert caught.value.detail == detail


def test_committed_episode_cannot_be_edited_or_deleted(monkeypatch) -> None:
    committed = _row(
        status="committed", background="背景", final_decision="接受实习", committed_at=NOW,
    )
    client = FakeClient([FakeResponse(200, [committed]), FakeResponse(200, [committed])])
    monkeypatch.setattr(decision_episode_service.httpx, "AsyncClient", lambda **_: client)

    with pytest.raises(HTTPException) as edit_error:
        asyncio.run(decision_episode_service.update_decision_episode(
            SETTINGS, USER, EPISODE_ID, DecisionEpisodeUpdate(background="修改"),
        ))
    with pytest.raises(HTTPException) as delete_error:
        asyncio.run(decision_episode_service.delete_decision_episode(
            SETTINGS, USER, EPISODE_ID,
        ))
    assert edit_error.value.status_code == 409
    assert delete_error.value.status_code == 409
