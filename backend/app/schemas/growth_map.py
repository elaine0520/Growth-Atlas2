"""Read-only Decision Timeline and Growth Map V1 transport schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.v2_common import (
    ActionItemStatus,
    ActionPlanStatus,
    DecisionEpisodeStatus,
    DecisionMemoryStatus,
    MemoryType,
)


class GrowthMapPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimelineActionItem(GrowthMapPayload):
    id: UUID
    description: str
    status: ActionItemStatus
    completed_at: datetime | None = None


class TimelineActionPlan(GrowthMapPayload):
    id: UUID
    objective: str
    status: ActionPlanStatus
    success_criteria: str | None = None
    confirmed_at: datetime | None = None
    actions: list[TimelineActionItem] = Field(default_factory=list)


class TimelineFeedback(GrowthMapPayload):
    id: UUID
    actual_outcome: str | None = None
    expected_vs_actual: str | None = None
    lessons_learned: list[str] = Field(default_factory=list)
    confirmed_at: datetime | None = None


class ConfirmedExperience(GrowthMapPayload):
    id: UUID
    source_candidate_id: UUID
    source_episode_id: UUID
    memory_type: MemoryType
    content: str
    status: DecisionMemoryStatus
    applicable_domains: list[str] = Field(default_factory=list)
    confirmed_at: datetime


class DecisionTimelineEntry(GrowthMapPayload):
    id: UUID
    title: str
    decision_question: str
    domain: str | None = None
    status: DecisionEpisodeStatus
    final_decision: str | None = None
    decision_rationale: str | None = None
    created_at: datetime
    committed_at: datetime | None = None
    closed_at: datetime | None = None
    action_plan: TimelineActionPlan | None = None
    feedback: list[TimelineFeedback] = Field(default_factory=list)
    confirmed_experiences: list[ConfirmedExperience] = Field(default_factory=list)


class GrowthMapResponse(GrowthMapPayload):
    timeline: list[DecisionTimelineEntry] = Field(default_factory=list)
    confirmed_experiences: list[ConfirmedExperience] = Field(default_factory=list)
    generated_at: datetime
