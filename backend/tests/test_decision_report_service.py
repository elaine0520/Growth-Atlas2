import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.schemas.reflection import AnalysisSection, DecisionReport
from app.services import decision_report_service


USER_ID = UUID("11111111-1111-1111-1111-111111111111")
CASE_ID = UUID("22222222-2222-2222-2222-222222222222")
REPORT_ID = UUID("33333333-3333-3333-3333-333333333333")
CREATED_AT = datetime.now(timezone.utc).isoformat()


def _report() -> DecisionReport:
    section = AnalysisSection(summary="真实 AI 总结", points=["真实 AI 要点"])
    return DecisionReport(
        goal_clarification=section,
        facts_analysis=section,
        constraints_analysis=section,
        options_comparison=section,
        decision_recommendation=section,
        action_plan=AnalysisSection(summary="今天联系导师", points=["18:00 前发送消息"]),
    )


class FakeResponse:
    def __init__(self, status_code: int, payload: list[dict[str, object]]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> list[dict[str, object]]:
        return self._payload


class FakeClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    async def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)


def test_save_persists_case_report_and_action_plan(monkeypatch) -> None:
    report = _report()
    case_row = {
        "id": str(CASE_ID),
        "user_question": "要不要参加实习？",
        "user_action": report.action_plan.model_dump(mode="json"),
    }
    report_row = {
        "id": str(REPORT_ID),
        "reflection_id": str(CASE_ID),
        "content": report.model_dump(mode="json"),
        "model_name": "moonshot-v1-8k",
        "prompt_version": "decision-v1",
        "created_at": CREATED_AT,
    }
    client = FakeClient([FakeResponse(201, [case_row]), FakeResponse(201, [report_row])])
    monkeypatch.setattr(decision_report_service.httpx, "AsyncClient", lambda **_: client)

    saved = asyncio.run(
        decision_report_service.save_decision_report(
            Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon"),
            CurrentUser(id=USER_ID, access_token="token"),
            "要不要参加实习？",
            report,
            model_name="moonshot-v1-8k",
            prompt_version="decision-v1",
        )
    )

    case_payload = client.calls[0][2]["json"]
    report_payload = client.calls[1][2]["json"]
    assert isinstance(case_payload, dict)
    assert isinstance(report_payload, dict)
    assert case_payload["user_action"] == report.action_plan.model_dump(mode="json")
    assert report_payload["content"] == report.model_dump(mode="json")
    assert report_payload["reflection_id"] == str(CASE_ID)
    assert saved.id == REPORT_ID
    assert saved.action_plan == report.action_plan


def test_read_reloads_report_and_linked_case(monkeypatch) -> None:
    report = _report()
    report_row = {
        "id": str(REPORT_ID),
        "reflection_id": str(CASE_ID),
        "content": report.model_dump(mode="json"),
        "model_name": "moonshot-v1-8k",
        "prompt_version": "decision-v1",
        "created_at": CREATED_AT,
    }
    case_row = {
        "id": str(CASE_ID),
        "user_question": "要不要参加实习？",
        "user_action": report.action_plan.model_dump(mode="json"),
    }
    client = FakeClient([FakeResponse(200, [report_row]), FakeResponse(200, [case_row])])
    monkeypatch.setattr(decision_report_service.httpx, "AsyncClient", lambda **_: client)

    saved = asyncio.run(
        decision_report_service.get_decision_report(
            Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon"),
            CurrentUser(id=USER_ID, access_token="token"),
            REPORT_ID,
        )
    )

    assert saved.question == "要不要参加实习？"
    assert saved.report == report
    assert client.calls[0][2]["params"] == {
        "id": f"eq.{REPORT_ID}", "user_id": f"eq.{USER_ID}", "select": "*"
    }
    assert client.calls[1][2]["params"] == {
        "id": f"eq.{CASE_ID}", "user_id": f"eq.{USER_ID}", "select": "*"
    }


def test_timeline_is_newest_first_and_scoped_to_current_user(monkeypatch) -> None:
    report = _report()
    older_id = UUID("44444444-4444-4444-4444-444444444444")
    reports = [
        {
            "id": str(REPORT_ID), "reflection_id": str(CASE_ID),
            "content": report.model_dump(mode="json"), "created_at": "2026-07-16T10:00:00Z",
        },
        {
            "id": str(older_id), "reflection_id": str(older_id),
            "content": report.model_dump(mode="json"), "created_at": "2026-07-15T10:00:00Z",
        },
    ]
    cases = [
        {"id": str(CASE_ID), "user_question": "new"},
        {"id": str(older_id), "user_question": "old"},
    ]
    client = FakeClient([FakeResponse(200, reports), FakeResponse(200, cases)])
    monkeypatch.setattr(decision_report_service.httpx, "AsyncClient", lambda **_: client)

    items = asyncio.run(decision_report_service.list_decision_timeline(
        Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon"),
        CurrentUser(id=USER_ID, access_token="token"),
    ))

    assert [item.question for item in items] == ["new", "old"]
    assert client.calls[0][2]["params"]["order"] == "created_at.desc,id.desc"
    assert client.calls[0][2]["params"]["user_id"] == f"eq.{USER_ID}"
    assert client.calls[1][2]["params"]["user_id"] == f"eq.{USER_ID}"


def test_timeline_returns_empty_without_loading_cases(monkeypatch) -> None:
    client = FakeClient([FakeResponse(200, [])])
    monkeypatch.setattr(decision_report_service.httpx, "AsyncClient", lambda **_: client)

    items = asyncio.run(decision_report_service.list_decision_timeline(
        Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon"),
        CurrentUser(id=USER_ID, access_token="token"),
    ))

    assert items == []
    assert len(client.calls) == 1
