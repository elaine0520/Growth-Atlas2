import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.models.v2_common import ActionItemStatus, ActionPlanStatus, FeedbackStatus
from app.schemas.v2_domain import (
    ActionItemCompletion,
    EpisodeActionPlanCreate,
    EpisodeFeedbackSubmit,
)
from app.services import action_feedback_service


USER_ID = UUID("11111111-1111-1111-1111-111111111111")
EPISODE_ID = UUID("22222222-2222-2222-2222-222222222222")
PLAN_ID = UUID("33333333-3333-3333-3333-333333333333")
ITEM_ID = UUID("44444444-4444-4444-4444-444444444444")
FEEDBACK_ID = UUID("55555555-5555-5555-5555-555555555555")
NOW = datetime.now(timezone.utc).isoformat()
SETTINGS = Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon")
USER = CurrentUser(id=USER_ID, access_token="token")


def _plan_row() -> dict[str, object]:
    return {
        "id": str(PLAN_ID), "user_id": str(USER_ID), "schema_version": "2.0",
        "decision_episode_id": str(EPISODE_ID), "source_report_draft_id": None,
        "status": "in_progress", "objective": "完成远程入职协商",
        "success_criteria": "获得书面确认", "key_assumptions": [],
        "major_obstacles": ["审批时间"], "fallback_plan": None, "review_at": None,
        "confirmed_at": NOW, "created_at": NOW, "updated_at": NOW,
    }


def _item_row(status: str = "pending") -> dict[str, object]:
    return {
        "id": str(ITEM_ID), "user_id": str(USER_ID), "schema_version": "2.0",
        "action_plan_id": str(PLAN_ID), "description": "联系招聘经理", "sequence": 1,
        "due_at": None, "status": status, "completion_note": None,
        "completed_at": NOW if status == "completed" else None,
        "created_at": NOW, "updated_at": NOW,
    }


def _feedback_row() -> dict[str, object]:
    return {
        "id": str(FEEDBACK_ID), "user_id": str(USER_ID), "schema_version": "2.0",
        "decision_episode_id": str(EPISODE_ID), "action_plan_id": str(PLAN_ID),
        "corrects_feedback_id": None, "feedback_type": "final_review", "status": "confirmed",
        "actual_actions": ["联系招聘经理"], "actual_outcome": "获得三个月远程安排",
        "expected_vs_actual": "与预期一致", "assumptions_validated": [],
        "assumptions_invalidated": [], "external_factors": [], "user_reflection": None,
        "lessons_learned": ["提前说明约束有助于谈判"], "future_adjustments": [],
        "occurred_at": NOW, "confirmed_at": NOW, "created_at": NOW, "updated_at": NOW,
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


def test_create_plan_persists_objective_actions_criteria_and_obstacles(monkeypatch) -> None:
    client = FakeClient([FakeResponse(200, [_plan_row()]), FakeResponse(200, [_item_row()])])
    monkeypatch.setattr(action_feedback_service.httpx, "AsyncClient", lambda **_: client)
    payload = EpisodeActionPlanCreate(
        objective="完成远程入职协商", actions=["联系招聘经理"],
        success_criteria="获得书面确认", major_obstacles=["审批时间"],
    )

    plan = asyncio.run(action_feedback_service.create_action_plan(
        SETTINGS, USER, EPISODE_ID, payload,
    ))

    assert plan.status == ActionPlanStatus.IN_PROGRESS
    assert plan.actions[0].description == "联系招聘经理"
    assert client.calls[0][2]["json"]["p_major_obstacles"] == ["审批时间"]


def test_action_item_can_be_completed(monkeypatch) -> None:
    client = FakeClient([FakeResponse(200, [_item_row("completed")])])
    monkeypatch.setattr(action_feedback_service.httpx, "AsyncClient", lambda **_: client)

    item = asyncio.run(action_feedback_service.complete_action_item(
        SETTINGS, USER, EPISODE_ID, PLAN_ID, ITEM_ID,
        ActionItemCompletion(completed=True),
    ))

    assert item.status == ActionItemStatus.COMPLETED
    assert item.completed_at is not None


def test_submit_feedback_records_outcome_without_memory_payload(monkeypatch) -> None:
    client = FakeClient([FakeResponse(200, [_feedback_row()])])
    monkeypatch.setattr(action_feedback_service.httpx, "AsyncClient", lambda **_: client)
    payload = EpisodeFeedbackSubmit(
        action_plan_id=PLAN_ID,
        actual_actions=["联系招聘经理"],
        actual_outcome="获得三个月远程安排",
        expected_vs_actual="与预期一致",
        lessons_learned=["提前说明约束有助于谈判"],
    )

    feedback = asyncio.run(action_feedback_service.submit_feedback(
        SETTINGS, USER, EPISODE_ID, payload,
    ))

    request_body = client.calls[0][2]["json"]
    assert feedback.status == FeedbackStatus.CONFIRMED
    assert feedback.actual_outcome == "获得三个月远程安排"
    assert feedback.lessons_learned == ["提前说明约束有助于谈判"]
    assert not any("memory" in key for key in request_body)
    assert client.calls[0][1].endswith("/rest/v1/rpc/submit_episode_feedback")
