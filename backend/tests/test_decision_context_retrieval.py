from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.models.decision_episode_v2 import DecisionEpisode
from app.models.decision_memory_v2 import DecisionMemory
from app.models.decision_profile_v2 import PersonalDecisionProfile, ProfileItem, StableProfile
from app.models.v2_common import DecisionMemoryStatus, MemoryType
from app.schemas.profile import ProfileResponse
from app.services.decision_context_retrieval import (
    DecisionContextRetrievalService,
    RetrievedDecisionContext,
)
from app.services.decision_draft_context_builder import DecisionDraftContextBuilder


USER_ID = UUID("11111111-1111-1111-1111-111111111111")
EPISODE_ID = UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime.now(timezone.utc)


def _episode() -> DecisionEpisode:
    return DecisionEpisode(
        id=EPISODE_ID, user_id=USER_ID, title="是否接受新工作",
        decision_question="我是否应该接受这份需要搬家的新工作？", domain="career",
        background="新工作薪资更高", goal="兼顾职业成长与家庭",
        created_at=NOW, updated_at=NOW,
    )


def _memory(
    content: str,
    *,
    status: DecisionMemoryStatus = DecisionMemoryStatus.ACTIVE,
    confidence: float = 0.8,
    domains: list[str] | None = None,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
) -> DecisionMemory:
    return DecisionMemory(
        id=uuid4(), user_id=USER_ID, source_candidate_id=uuid4(),
        memory_type=MemoryType.CONFIRMED_LESSON, content=content,
        applicable_domains=domains or [], evidence=[], confidence=confidence,
        status=status, effective_from=effective_from, effective_until=effective_until,
        confirmed_at=NOW - timedelta(days=30), created_at=NOW, updated_at=NOW,
    )


def _profile() -> ProfileResponse:
    return ProfileResponse(
        id=USER_ID,
        user_info={"life_stage": "职业早期"},
        current_context="正在评估职业机会",
        short_term_goals=["找到成长空间"], long_term_goals=["保持家庭稳定"],
        values=["成长", "家庭"], status="confirmed", version=3,
        confirmed_at=NOW, created_at=NOW, updated_at=NOW,
    )


def test_memory_retrieval_filters_relevance_validity_status_and_confidence() -> None:
    relevant = _memory("搬家前先协商远程安排", domains=["career"])
    expired = _memory(
        "旧的职业经验", domains=["career"], effective_until=NOW - timedelta(days=1),
    )
    future = _memory(
        "未来才生效", domains=["career"], effective_from=NOW + timedelta(days=1),
    )
    low_confidence = _memory("低置信度职业经验", domains=["career"], confidence=0.2)
    disabled = _memory(
        "已经禁用", domains=["career"], status=DecisionMemoryStatus.DISABLED,
    )
    unrelated = _memory("烘焙面包时控制温度", domains=["cooking"])

    selected = DecisionContextRetrievalService.filter_memories(
        _episode(), [relevant, expired, future, low_confidence, disabled, unrelated], NOW,
    )

    assert [item.memory.id for item in selected] == [relevant.id]
    assert selected[0].relevance > 0.5


def test_history_retrieval_keeps_related_past_episode_only() -> None:
    related_id = uuid4()
    rows = [
        {
            "id": str(related_id), "domain": "career",
            "decision_question": "是否接受需要通勤的新工作？",
            "final_decision": "先协商远程办公", "decision_rationale": "兼顾家庭",
            "closed_at": (NOW - timedelta(days=200)).isoformat(), "updated_at": NOW.isoformat(),
        },
        {
            "id": str(uuid4()), "domain": "cooking", "decision_question": "是否买烤箱？",
            "final_decision": "购买", "decision_rationale": None,
            "closed_at": NOW.isoformat(), "updated_at": NOW.isoformat(),
        },
    ]

    selected = DecisionContextRetrievalService.filter_history(_episode(), rows, NOW)

    assert [item.id for item in selected] == [related_id]


def test_context_snapshot_records_every_selected_source() -> None:
    memory = _memory("搬家前先协商远程安排", domains=["career"])
    relevant_memory = DecisionContextRetrievalService.filter_memories(
        _episode(), [memory], NOW,
    )[0]
    history = DecisionContextRetrievalService.filter_history(
        _episode(), [{
            "id": str(uuid4()), "domain": "career", "decision_question": "过去的职业选择",
            "final_decision": "选择远程", "decision_rationale": "家庭稳定",
            "closed_at": NOW.isoformat(), "updated_at": NOW.isoformat(),
        }], NOW,
    )
    retrieved = RetrievedDecisionContext(
        profile=_profile(), memories=[relevant_memory], historical_episodes=history,
        retrieved_at=NOW,
    )

    context = DecisionDraftContextBuilder().build(_episode(), "system", retrieved)

    assert context.snapshot["profile_version"] == 3
    assert context.snapshot["selected_memory_ids"] == [str(memory.id)]
    assert context.snapshot["selected_historical_episode_ids"] == [str(history[0].id)]
    assert str(memory.id) in context.user_prompt
    assert history[0].final_decision in context.user_prompt
    assert "当前决策中的用户说明优先于旧资料" in context.user_prompt


def test_v2_profile_formatter_uses_only_confirmed_time_valid_items() -> None:
    active = ProfileItem(content="保持家庭稳定", confirmed_at=NOW)
    expired = ProfileItem(
        content="过去阶段目标", confirmed_at=NOW - timedelta(days=100),
        effective_until=NOW - timedelta(days=1),
    )
    unconfirmed = ProfileItem(content="未经确认的目标")
    profile = PersonalDecisionProfile(
        id=uuid4(), user_id=USER_ID, status="confirmed", version=2,
        stable_profile=StableProfile(long_term_goals=[active, expired, unconfirmed]),
        confirmed_at=NOW, created_at=NOW, updated_at=NOW,
    )
    retrieved = RetrievedDecisionContext(profile=profile, retrieved_at=NOW)

    context = DecisionDraftContextBuilder().build(_episode(), "system", retrieved)

    assert "保持家庭稳定" in context.user_prompt
    assert "过去阶段目标" not in context.user_prompt
    assert "未经确认的目标" not in context.user_prompt
    assert context.snapshot["profile_version"] == 2
