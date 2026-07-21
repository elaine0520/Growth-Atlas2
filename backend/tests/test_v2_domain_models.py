"""Contract tests for the Growth Atlas V2 domain foundation."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import (
    ActionItemV2,
    ActionPlanV2,
    DecisionEpisode,
    DecisionMemory,
    DecisionReportDraft,
    FeedbackV2,
    MemoryCandidate,
    PersonalDecisionProfile,
    V2_SCHEMA_VERSION,
)
from app.models.decision_profile_v2 import DecisionStyleObservation, ProfileItem, StableProfile
from app.models.v2_common import (
    ACTION_PLAN_TRANSITIONS,
    DECISION_EPISODE_TRANSITIONS,
    ActionItemStatus,
    ActionPlanStatus,
    DecisionEpisodeStatus,
    FeedbackType,
    MemoryType,
    can_transition,
)
from app.schemas.v2_domain import DecisionEpisodeCreate, PersonalDecisionProfileDraft


USER_ID = uuid4()
EPISODE_ID = uuid4()


def test_v2_entities_share_schema_version() -> None:
    profile = PersonalDecisionProfile(user_id=USER_ID)
    episode = DecisionEpisode(
        user_id=USER_ID,
        title="选择研究方向",
        decision_question="我应该选择哪个研究方向？",
    )
    report = DecisionReportDraft(user_id=USER_ID, decision_episode_id=episode.id)

    assert profile.schema_version == V2_SCHEMA_VERSION
    assert episode.schema_version == V2_SCHEMA_VERSION
    assert report.schema_version == V2_SCHEMA_VERSION


def test_profile_separates_stable_context_and_evidence_based_style() -> None:
    episode_id = uuid4()
    profile = PersonalDecisionProfile(
        user_id=USER_ID,
        stable_profile=StableProfile(
            long_term_goals=[ProfileItem(content="进入人工智能研究领域")]
        ),
        decision_style=[
            DecisionStyleObservation(
                domain="education",
                observation="在高不确定选择中倾向先做低成本验证",
                supporting_episode_ids=[episode_id],
                evidence_count=1,
                confidence=0.4,
            )
        ],
    )

    assert profile.stable_profile.long_term_goals[0].content == "进入人工智能研究领域"
    assert profile.decision_style[0].user_confirmed is False


def test_decision_episode_lifecycle_rejects_skipping_user_decision() -> None:
    assert can_transition(
        DecisionEpisodeStatus.CAPTURING,
        DecisionEpisodeStatus.READY_FOR_ANALYSIS,
        DECISION_EPISODE_TRANSITIONS,
    )
    assert not can_transition(
        DecisionEpisodeStatus.DRAFT_READY,
        DecisionEpisodeStatus.COMMITTED,
        DECISION_EPISODE_TRANSITIONS,
    )


def test_action_plan_requires_explicit_confirmation_before_execution() -> None:
    item = ActionItemV2(
        description="联系导师确认项目范围",
        sequence=1,
        status=ActionItemStatus.PENDING,
    )
    plan = ActionPlanV2(
        user_id=USER_ID,
        decision_episode_id=EPISODE_ID,
        objective="验证研究项目是否适合当前目标",
        actions=[item],
    )

    assert plan.status == ActionPlanStatus.DRAFT
    assert not can_transition(
        ActionPlanStatus.DRAFT,
        ActionPlanStatus.IN_PROGRESS,
        ACTION_PLAN_TRANSITIONS,
    )


def test_feedback_is_draft_until_user_confirmation() -> None:
    feedback = FeedbackV2(
        user_id=USER_ID,
        decision_episode_id=EPISODE_ID,
        feedback_type=FeedbackType.CHECKPOINT,
        actual_actions=["完成了导师访谈"],
    )

    assert feedback.status.value == "draft"
    assert feedback.confirmed_at is None


def test_memory_candidate_does_not_become_active_memory_implicitly() -> None:
    candidate = MemoryCandidate(
        user_id=USER_ID,
        decision_episode_id=EPISODE_ID,
        candidate_type=MemoryType.EFFECTIVE_STRATEGY,
        proposed_content="面对高不确定选择时，先访谈再投入",
        rationale="本次行动降低了信息不足带来的风险",
    )

    assert candidate.status.value == "suggested"

    with pytest.raises(ValidationError):
        DecisionMemory.model_validate(
            {
                "user_id": USER_ID,
                "source_candidate_id": candidate.id,
                "memory_type": MemoryType.EFFECTIVE_STRATEGY,
                "content": candidate.proposed_content,
            }
        )

    memory = DecisionMemory(
        user_id=USER_ID,
        source_candidate_id=candidate.id,
        memory_type=MemoryType.EFFECTIVE_STRATEGY,
        content=candidate.proposed_content,
        confirmed_at=datetime.now(timezone.utc),
    )
    assert memory.status.value == "active"


def test_transport_schemas_do_not_accept_client_owned_user_id() -> None:
    with pytest.raises(ValidationError):
        DecisionEpisodeCreate.model_validate(
            {
                "user_id": USER_ID,
                "title": "研究方向",
                "decision_question": "选择哪个研究方向？",
            }
        )

    draft = PersonalDecisionProfileDraft()
    assert "user_id" not in draft.model_dump()
