from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.routes import reflection as reflection_route
from app.core.auth import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.main import app
from app.schemas.profile import ProfileResponse
from app.schemas.reflection import AnalysisSection, DecisionReport, SavedDecisionReport
from app.services.ai_analysis_service import AIAnalysisService
from app.services.context_builder import CONTEXT_VERSION, MAX_CONTEXT_CHARS, ContextBuilder


USER_ID = UUID("11111111-1111-1111-1111-111111111111")
REPORT_ID = UUID("22222222-2222-2222-2222-222222222222")
CASE_ID = UUID("33333333-3333-3333-3333-333333333333")


def _profile(
    *,
    values: list[str] | None = None,
    goals: list[str] | None = None,
    context: str = "正在备考研究生，每周可自由安排的时间有限",
) -> ProfileResponse:
    now = datetime.now(timezone.utc)
    return ProfileResponse(
        id=USER_ID,
        user_info={
            "nickname": "小林",
            "age_range": "18-24",
            "life_stage": "大学生",
            "background": "计算机专业大三",
            "locale": "zh-CN",
            "timezone": "Asia/Shanghai",
        },
        current_context=context,
        pressure_sources=["备考时间紧张"],
        short_term_goals=goals or ["通过研究生考试"],
        long_term_goals=["从事人工智能研究"],
        values=values or ["长期成长", "稳定"],
        self_description=["偏好先做低成本验证"],
        status="confirmed",
        version=3,
        confirmed_at=now,
        last_reviewed_at=now,
        created_at=now,
        updated_at=now,
    )


def _report() -> DecisionReport:
    section = AnalysisSection(summary="测试总结", points=["测试要点"])
    return DecisionReport(
        goal_clarification=section,
        facts_analysis=section,
        constraints_analysis=section,
        options_comparison=section,
        decision_recommendation=section,
        action_plan=section,
    )


def _saved_report(question: str) -> SavedDecisionReport:
    report = _report()
    return SavedDecisionReport(
        id=REPORT_ID,
        decision_case_id=CASE_ID,
        question=question,
        report=report,
        action_plan=report.action_plan,
        model_name="moonshot-v1-8k",
        prompt_version="decision-v1",
        created_at=datetime.now(timezone.utc),
    )


def _override_user() -> CurrentUser:
    return CurrentUser(id=USER_ID, access_token="user-token")


def test_analyze_reflection_loads_current_users_profile(monkeypatch) -> None:
    loaded: dict[str, object] = {}
    expected_profile = _profile()

    async def fake_get_profile(settings: Settings, user: CurrentUser) -> ProfileResponse:
        loaded["user"] = user
        return expected_profile

    async def fake_analyze(
        self: AIAnalysisService, question: str, profile: ProfileResponse
    ) -> DecisionReport:
        loaded["question"] = question
        loaded["profile"] = profile
        return _report()

    async def fake_save(
        settings: Settings,
        user: CurrentUser,
        question: str,
        report: DecisionReport,
        *,
        model_name: str,
        prompt_version: str,
    ) -> SavedDecisionReport:
        loaded["saved_user"] = user
        loaded["saved_report"] = report
        loaded["model_name"] = model_name
        loaded["prompt_version"] = prompt_version
        return _saved_report(question)

    monkeypatch.setattr(reflection_route, "get_profile", fake_get_profile)
    monkeypatch.setattr(reflection_route.AIAnalysisService, "analyze", fake_analyze)
    monkeypatch.setattr(reflection_route, "save_decision_report", fake_save)
    app.dependency_overrides[get_settings] = lambda: Settings(kimi_api_key="test-key")
    app.dependency_overrides[get_current_user] = _override_user
    try:
        response = TestClient(app).post(
            "/api/reflection/analyze",
            json={"question": "我应该接受新工作还是留在现在的团队？"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert loaded["user"] == _override_user()
    assert loaded["profile"] == expected_profile
    assert loaded["question"] == "我应该接受新工作还是留在现在的团队？"
    assert loaded["saved_user"] == _override_user()
    assert loaded["saved_report"] == _report()
    assert loaded["prompt_version"] == "decision-v1"
    assert response.json()["id"] == str(REPORT_ID)


def test_saved_decision_report_can_be_read_again(monkeypatch) -> None:
    question = "我应该接受新工作还是留在现在的团队？"

    async def fake_read(
        settings: Settings, user: CurrentUser, report_id: UUID
    ) -> SavedDecisionReport:
        assert user == _override_user()
        assert report_id == REPORT_ID
        return _saved_report(question)

    monkeypatch.setattr(reflection_route, "get_decision_report", fake_read)
    app.dependency_overrides[get_settings] = lambda: Settings(
        supabase_url="https://example.supabase.co", supabase_anon_key="anon"
    )
    app.dependency_overrides[get_current_user] = _override_user
    try:
        response = TestClient(app).get(f"/api/reflection/reports/{REPORT_ID}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["question"] == question
    assert response.json()["report"]["action_plan"] == response.json()["action_plan"]


def test_analyze_reflection_requires_access_token() -> None:
    response = TestClient(app).post(
        "/api/reflection/analyze",
        json={"question": "我应该接受新工作还是留在现在的团队？"},
    )
    assert response.status_code == 401


def test_analyze_reflection_requires_api_key() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(kimi_api_key=None)
    app.dependency_overrides[get_current_user] = _override_user
    try:
        response = TestClient(app).post(
            "/api/reflection/analyze",
            json={"question": "我应该接受新工作还是留在现在的团队？"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


def test_context_builder_sends_only_profile_and_current_question() -> None:
    context = ContextBuilder().build(
        "要不要接一个会占用周末的实习？",
        _profile(),
        "system rules",
    )

    assert context.version == CONTEXT_VERSION
    assert len(context.profile_context) <= MAX_CONTEXT_CHARS
    assert len(context.messages) == 2
    assert [message["role"] for message in context.messages] == ["system", "user"]
    assert "通过研究生考试" in context.user_prompt
    assert "备考时间紧张" in context.user_prompt
    assert "要不要接一个会占用周末的实习？" in context.user_prompt
    assert "conversation_history" not in context.user_prompt
    assert "历史消息" not in context.user_prompt


def test_different_profiles_change_the_kimi_prompt_for_the_same_question() -> None:
    builder = ContextBuilder()
    question = "我是否要接受需要频繁出差的新工作？"
    growth_context = builder.build(
        question,
        _profile(values=["快速成长"], goals=["一年内拓展行业经验"]),
        "system rules",
    )
    stability_context = builder.build(
        question,
        _profile(values=["家庭陪伴", "稳定"], goals=["保持规律生活"]),
        "system rules",
    )

    assert growth_context.user_prompt != stability_context.user_prompt
    assert "快速成长" in growth_context.user_prompt
    assert "家庭陪伴" in stability_context.user_prompt
    assert "必须把档案中的目标、价值排序、现实情境和压力用于方案比较与建议" in growth_context.user_prompt
