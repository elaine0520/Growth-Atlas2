import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.models.v2_common import DecisionEpisodeStatus
from app.schemas.v2_domain import DecisionEpisodeConfirm
from app.services import decision_draft_service


USER_ID = UUID("11111111-1111-1111-1111-111111111111")
EPISODE_ID = UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime.now(timezone.utc).isoformat()
SETTINGS = Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon")
USER = CurrentUser(id=USER_ID, access_token="token")


def _committed_row() -> dict[str, object]:
    return {
        "id": str(EPISODE_ID),
        "user_id": str(USER_ID),
        "schema_version": "2.0",
        "title": "是否接受新工作",
        "decision_question": "我是否应该接受这份新工作？",
        "domain": "career",
        "importance": 5,
        "background": "需要搬家",
        "context_snapshot": None,
        "goal": "兼顾家庭与成长",
        "values_data": ["家庭", "成长"],
        "facts": [],
        "assumptions": [],
        "unknowns": [],
        "constraints_data": [],
        "options": [],
        "final_decision": "先协商远程入职",
        "decision_rationale": "这更符合我的家庭约束",
        "evidence": [],
        "status": "committed",
        "profile_version_id": None,
        "confirmed_from_draft_id": str(DRAFT_ID),
        "committed_at": NOW,
        "closed_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }


class FakeResponse:
    status_code = 200

    def json(self) -> list[dict[str, object]]:
        return [_committed_row()]


class FakeClient:
    def __init__(self) -> None:
        self.url = ""
        self.body: dict[str, object] = {}

    async def __aenter__(self) -> "FakeClient": return self
    async def __aexit__(self, *args: object) -> None: return None

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.url = url
        self.body = kwargs["json"]  # type: ignore[assignment]
        return FakeResponse()


def test_confirm_keeps_ai_draft_reference_and_user_decision_separate(monkeypatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(decision_draft_service.httpx, "AsyncClient", lambda **_: client)
    payload = DecisionEpisodeConfirm(
        draft_id=DRAFT_ID,
        final_decision="先协商远程入职",
        decision_rationale="这更符合我的家庭约束",
    )

    episode = asyncio.run(decision_draft_service.confirm_user_decision(
        SETTINGS, USER, EPISODE_ID, payload,
    ))

    assert episode.status == DecisionEpisodeStatus.COMMITTED
    assert episode.final_decision == "先协商远程入职"
    assert episode.confirmed_from_draft_id == DRAFT_ID
    assert client.body["p_draft_id"] == str(DRAFT_ID)
    assert client.body["p_final_decision"] == "先协商远程入职"
    assert client.url.endswith("/rest/v1/rpc/confirm_decision_episode")
