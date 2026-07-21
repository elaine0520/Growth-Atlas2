import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

from app.core.config import Settings
from app.models.decision_episode_v2 import DecisionEpisode
from app.services.ai_decision_draft_service import AIDecisionDraftService


USER_ID = UUID("11111111-1111-1111-1111-111111111111")
EPISODE_ID = UUID("22222222-2222-2222-2222-222222222222")


def _episode() -> DecisionEpisode:
    now = datetime.now(timezone.utc)
    return DecisionEpisode(
        id=EPISODE_ID,
        user_id=USER_ID,
        title="是否接受新工作",
        decision_question="我是否应该接受这份新工作？",
        background="新工作薪资更高，但需要搬家。",
        goal="做出兼顾成长与家庭的选择",
        values=["家庭", "成长"],
        facts=["薪资提高 20%"],
        assumptions=["新团队有成长空间"],
        unknowns=["实际团队文化"],
        constraints=["三个月内不能搬家"],
        options=["接受", "拒绝", "协商远程入职"],
        created_at=now,
        updated_at=now,
    )


class FakeCompletions:
    async def create(self, **_: object) -> object:
        payload = {
            "goal_clarification": {"summary": "平衡成长与家庭", "points": []},
            "values_analysis": {"summary": "家庭与成长均重要", "points": []},
            "facts_analysis": {"summary": "已知薪资提高", "points": ["薪资提高 20%"]},
            "assumptions": ["新团队有成长空间"],
            "uncertainty": ["团队文化尚未验证"],
            "constraints_analysis": {"summary": "短期不能搬家", "points": []},
            "options": [
                {
                    "name": "协商远程入职",
                    "benefits": ["兼顾机会与家庭"],
                    "costs": ["需要谈判"],
                    "risks": ["公司可能拒绝"],
                    "opportunity_costs": ["延迟融入团队"],
                    "long_term_impacts": ["保留职业成长机会"],
                    "reversibility": "可在三个月后重新评估搬家",
                }
            ],
            "recommendation": {"summary": "优先协商远程入职", "points": []},
            "recommendation_conditions": ["公司允许远程"],
            "change_conditions": ["团队文化调查结果不佳"],
        }
        message = SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class InvalidThenValidCompletions:
    def __init__(self, always_invalid: bool = False) -> None:
        self.calls = 0
        self.always_invalid = always_invalid

    async def create(self, **kwargs: object) -> object:
        self.calls += 1
        if self.always_invalid or self.calls == 1:
            message = SimpleNamespace(content='{"recommendation": {}}')
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])
        return await FakeCompletions().create(**kwargs)


def test_ai_output_is_a_complete_reviewable_draft() -> None:
    service = AIDecisionDraftService(Settings(kimi_api_key="test-key"))
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    content, context = asyncio.run(service.generate(_episode(), None))

    assert content.goal_clarification.summary
    assert content.values_analysis.summary
    assert content.facts_analysis.summary
    assert content.uncertainty
    assert content.constraints_analysis.summary
    assert content.options[0].risks
    assert content.options[0].opportunity_costs
    assert content.options[0].reversibility
    assert content.recommendation.summary
    assert "不得替用户作出最终决定" in context.user_prompt
    assert context.snapshot["selected_memory_ids"] == []


def test_draft_schema_rejects_final_decision_field() -> None:
    schema = AIDecisionDraftService(Settings(kimi_api_key="test-key")).build_context(
        _episode(), None
    ).system_prompt

    assert '"final_decision"' not in schema
    assert "只能是一份供用户审阅的草稿" in schema


def test_ai_retries_invalid_structured_output() -> None:
    completions = InvalidThenValidCompletions()
    service = AIDecisionDraftService(
        Settings(kimi_api_key="test-key", ai_output_attempts=2)
    )
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    content, _ = asyncio.run(service.generate(_episode(), None))

    assert content.recommendation.summary
    assert completions.calls == 2


def test_ai_fails_closed_after_invalid_output_limit() -> None:
    completions = InvalidThenValidCompletions(always_invalid=True)
    service = AIDecisionDraftService(
        Settings(kimi_api_key="test-key", ai_output_attempts=2)
    )
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    try:
        asyncio.run(service.generate(_episode(), None))
    except RuntimeError as exc:
        assert "invalid decision draft" in str(exc)
    else:
        raise AssertionError("Invalid output must not be persisted as a draft")

    assert completions.calls == 2
