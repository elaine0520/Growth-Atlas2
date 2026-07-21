"""Transport schemas for the Growth Atlas V2 domain foundation.

Ownership is intentionally absent from create/update payloads. API routes must
derive ``user_id`` from the authenticated access token.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.action_plan_v2 import ActionItemV2
from app.models.decision_profile_v2 import DecisionStyleObservation, DynamicContext, StableProfile
from app.models.decision_report_draft_v2 import DecisionOptionV2, ReportSectionV2
from app.models.v2_common import (
    ActionPlanStatus,
    DecisionEpisodeStatus,
    DecisionMemoryStatus,
    FeedbackStatus,
    FeedbackType,
    MemoryCandidateStatus,
    MemoryType,
    ProfileStatus,
    ReportDraftStatus,
    V2_SCHEMA_VERSION,
)


class V2Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=V2_SCHEMA_VERSION, frozen=True)


class PersonalDecisionProfileDraft(V2Payload):
    stable_profile: StableProfile = Field(default_factory=StableProfile)
    dynamic_context: DynamicContext = Field(default_factory=DynamicContext)
    decision_style: list[DecisionStyleObservation] = Field(default_factory=list)
    supersedes_profile_id: UUID | None = None


class PersonalDecisionProfileTransition(V2Payload):
    target_status: ProfileStatus
    reason: str | None = Field(default=None, max_length=1_000)


class DecisionEpisodeCreate(V2Payload):
    title: str = Field(min_length=1, max_length=200)
    decision_question: str = Field(min_length=3, max_length=10_000)
    domain: str | None = Field(default=None, max_length=100)
    importance: int | None = Field(default=None, ge=1, le=5)
    profile_version_id: UUID | None = None


class DecisionEpisodeUpdate(V2Payload):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    decision_question: str | None = Field(default=None, min_length=3, max_length=10_000)
    domain: str | None = Field(default=None, max_length=100)
    importance: int | None = Field(default=None, ge=1, le=5)
    background: str | None = Field(default=None, max_length=5_000)
    goal: str | None = Field(default=None, max_length=3_000)
    values: list[str] | None = None
    facts: list[str] | None = None
    assumptions: list[str] | None = None
    unknowns: list[str] | None = None
    constraints: list[str] | None = None
    options: list[str] | None = None
    final_decision: str | None = Field(default=None, max_length=5_000)
    decision_rationale: str | None = Field(default=None, max_length=5_000)


class DecisionEpisodeTransition(V2Payload):
    target_status: DecisionEpisodeStatus
    reason: str | None = Field(default=None, max_length=1_000)


class DecisionEpisodeConfirm(V2Payload):
    draft_id: UUID
    final_decision: str = Field(min_length=1, max_length=5_000)
    decision_rationale: str | None = Field(default=None, max_length=5_000)


class DecisionEpisodeListItem(V2Payload):
    id: UUID
    title: str
    decision_question: str
    domain: str | None = None
    status: DecisionEpisodeStatus
    created_at: datetime
    updated_at: datetime


class DecisionReportDraftCreate(V2Payload):
    decision_episode_id: UUID
    version: int = Field(default=1, ge=1)
    goal_clarification: ReportSectionV2 | None = None
    values_analysis: ReportSectionV2 | None = None
    facts_analysis: ReportSectionV2 | None = None
    assumptions: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    constraints_analysis: ReportSectionV2 | None = None
    options: list[DecisionOptionV2] = Field(default_factory=list)
    recommendation: ReportSectionV2 | None = None
    recommendation_conditions: list[str] = Field(default_factory=list)
    change_conditions: list[str] = Field(default_factory=list)
    proposed_action_plan: ReportSectionV2 | None = None
    feedback_plan: ReportSectionV2 | None = None
    model_provider: str | None = Field(default=None, max_length=100)
    model_name: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=50)
    context_version: str | None = Field(default=None, max_length=50)
    context_snapshot_id: UUID | None = None


class DecisionReportDraftTransition(V2Payload):
    target_status: ReportDraftStatus
    reason: str | None = Field(default=None, max_length=1_000)


class ActionPlanCreate(V2Payload):
    decision_episode_id: UUID
    source_report_draft_id: UUID | None = None
    objective: str = Field(min_length=1, max_length=3_000)
    actions: list[ActionItemV2] = Field(default_factory=list)
    success_criteria: str | None = Field(default=None, max_length=2_000)
    key_assumptions: list[str] = Field(default_factory=list)
    major_obstacles: list[str] = Field(default_factory=list)
    fallback_plan: str | None = Field(default=None, max_length=2_000)
    review_at: datetime | None = None


class ActionPlanTransition(V2Payload):
    target_status: ActionPlanStatus
    reason: str | None = Field(default=None, max_length=1_000)


class EpisodeActionPlanCreate(V2Payload):
    objective: str = Field(min_length=1, max_length=3_000)
    actions: list[str] = Field(min_length=1)
    success_criteria: str | None = Field(default=None, max_length=2_000)
    major_obstacles: list[str] = Field(default_factory=list)


class ActionItemCompletion(V2Payload):
    completed: bool
    completion_note: str | None = Field(default=None, max_length=2_000)


class FeedbackCreate(V2Payload):
    decision_episode_id: UUID
    action_plan_id: UUID | None = None
    feedback_type: FeedbackType
    actual_actions: list[str] = Field(default_factory=list)
    actual_outcome: str | None = Field(default=None, max_length=5_000)
    expected_vs_actual: str | None = Field(default=None, max_length=5_000)
    assumptions_validated: list[str] = Field(default_factory=list)
    assumptions_invalidated: list[str] = Field(default_factory=list)
    external_factors: list[str] = Field(default_factory=list)
    user_reflection: str | None = Field(default=None, max_length=5_000)
    lessons_learned: list[str] = Field(default_factory=list)
    future_adjustments: list[str] = Field(default_factory=list)
    occurred_at: datetime | None = None


class FeedbackTransition(V2Payload):
    target_status: FeedbackStatus
    reason: str | None = Field(default=None, max_length=1_000)


class EpisodeFeedbackSubmit(V2Payload):
    action_plan_id: UUID
    actual_actions: list[str] = Field(default_factory=list)
    actual_outcome: str = Field(min_length=1, max_length=5_000)
    expected_vs_actual: str = Field(min_length=1, max_length=5_000)
    lessons_learned: list[str] = Field(min_length=1)


class MemoryCandidateCreate(V2Payload):
    decision_episode_id: UUID
    feedback_id: UUID | None = None
    candidate_type: MemoryType
    proposed_content: str = Field(min_length=1, max_length=5_000)
    rationale: str = Field(min_length=1, max_length=2_000)
    applicable_domains: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    proposed_expires_at: datetime | None = None


class MemoryCandidateTransition(V2Payload):
    target_status: MemoryCandidateStatus
    edited_content: str | None = Field(default=None, min_length=1, max_length=5_000)
    reason: str | None = Field(default=None, max_length=1_000)


class FeedbackMemoryCandidateCreate(V2Payload):
    feedback_id: UUID
    candidate_type: MemoryType
    proposed_content: str = Field(min_length=1, max_length=5_000)
    rationale: str = Field(min_length=1, max_length=2_000)
    applicable_domains: list[str] = Field(default_factory=list)


class MemoryCandidateConfirm(V2Payload):
    content: str = Field(min_length=1, max_length=5_000)
    applicable_domains: list[str] = Field(default_factory=list)
    user_confirmed: Literal[True]


class MemoryCandidateReject(V2Payload):
    reason: str | None = Field(default=None, max_length=1_000)


class DecisionMemoryCreate(V2Payload):
    source_candidate_id: UUID
    memory_type: MemoryType
    content: str = Field(min_length=1, max_length=5_000)
    applicable_domains: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    review_after: datetime | None = None
    confirmed_at: datetime
    supersedes_memory_id: UUID | None = None


class DecisionMemoryTransition(V2Payload):
    target_status: DecisionMemoryStatus
    reason: str | None = Field(default=None, max_length=1_000)


class DecisionMemoryManage(V2Payload):
    target_status: Literal["active", "disabled"]
