"""Shared contracts for the Growth Atlas V2 decision domain."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


V2_SCHEMA_VERSION = "2.0"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProfileStatus(StrEnum):
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class DecisionEpisodeStatus(StrEnum):
    CAPTURING = "capturing"
    READY_FOR_ANALYSIS = "ready_for_analysis"
    ANALYZING = "analyzing"
    DRAFT_READY = "draft_ready"
    AWAITING_USER_DECISION = "awaiting_user_decision"
    COMMITTED = "committed"
    ACTING = "acting"
    AWAITING_FEEDBACK = "awaiting_feedback"
    REFLECTED = "reflected"
    ARCHIVED = "archived"
    ANALYSIS_FAILED = "analysis_failed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"


class ReportDraftStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    INVALID = "invalid"
    GENERATION_FAILED = "generation_failed"


class ActionPlanStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    SUPERSEDED = "superseded"


class ActionItemStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class FeedbackStatus(StrEnum):
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    ARCHIVED = "archived"


class FeedbackType(StrEnum):
    CHECKPOINT = "checkpoint"
    OUTCOME = "outcome"
    REFLECTION = "reflection"
    FINAL_REVIEW = "final_review"


class MemoryCandidateStatus(StrEnum):
    SUGGESTED = "suggested"
    EDITED = "edited"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DecisionMemoryStatus(StrEnum):
    ACTIVE = "active"
    NEEDS_REVIEW = "needs_review"
    SUPERSEDED = "superseded"
    DISABLED = "disabled"
    ARCHIVED = "archived"
    DELETED = "deleted"


class EvidenceSourceType(StrEnum):
    USER_INPUT = "user_input"
    USER_CONFIRMED = "user_confirmed"
    DECISION_EPISODE = "decision_episode"
    FEEDBACK = "feedback"
    AI_OBSERVATION = "ai_observation"
    LEGACY_IMPORT = "legacy_import"


class MemoryType(StrEnum):
    DECISION_EXPERIENCE = "decision_experience"
    CONFIRMED_LESSON = "confirmed_lesson"
    EFFECTIVE_STRATEGY = "effective_strategy"
    KNOWN_CONSTRAINT = "known_constraint"
    DECISION_PATTERN = "decision_pattern"
    PROFILE_CHANGE = "profile_change"


class V2DomainModel(BaseModel):
    """Persistence-agnostic identity and audit fields shared by V2 entities."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    schema_version: str = Field(default=V2_SCHEMA_VERSION, frozen=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EvidenceReferenceV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: EvidenceSourceType
    source_id: UUID | None = None
    note: str | None = Field(default=None, max_length=1_000)


StatusT = TypeVar("StatusT", bound=StrEnum)


def can_transition(
    current: StatusT,
    target: StatusT,
    transitions: dict[StatusT, frozenset[StatusT]],
) -> bool:
    """Return whether a lifecycle transition is explicitly allowed."""

    return target in transitions.get(current, frozenset())


PROFILE_TRANSITIONS = {
    ProfileStatus.DRAFT: frozenset({ProfileStatus.PENDING_CONFIRMATION, ProfileStatus.ARCHIVED}),
    ProfileStatus.PENDING_CONFIRMATION: frozenset(
        {ProfileStatus.DRAFT, ProfileStatus.CONFIRMED, ProfileStatus.ARCHIVED}
    ),
    ProfileStatus.CONFIRMED: frozenset({ProfileStatus.SUPERSEDED, ProfileStatus.ARCHIVED}),
    ProfileStatus.SUPERSEDED: frozenset({ProfileStatus.ARCHIVED}),
    ProfileStatus.ARCHIVED: frozenset(),
}

DECISION_EPISODE_TRANSITIONS = {
    DecisionEpisodeStatus.CAPTURING: frozenset(
        {DecisionEpisodeStatus.READY_FOR_ANALYSIS, DecisionEpisodeStatus.CANCELLED}
    ),
    DecisionEpisodeStatus.READY_FOR_ANALYSIS: frozenset(
        {DecisionEpisodeStatus.ANALYZING, DecisionEpisodeStatus.CAPTURING, DecisionEpisodeStatus.CANCELLED}
    ),
    DecisionEpisodeStatus.ANALYZING: frozenset(
        {DecisionEpisodeStatus.DRAFT_READY, DecisionEpisodeStatus.ANALYSIS_FAILED}
    ),
    DecisionEpisodeStatus.ANALYSIS_FAILED: frozenset(
        {DecisionEpisodeStatus.ANALYZING, DecisionEpisodeStatus.CAPTURING, DecisionEpisodeStatus.ABANDONED}
    ),
    DecisionEpisodeStatus.DRAFT_READY: frozenset(
        {DecisionEpisodeStatus.AWAITING_USER_DECISION, DecisionEpisodeStatus.ANALYZING}
    ),
    DecisionEpisodeStatus.AWAITING_USER_DECISION: frozenset(
        {DecisionEpisodeStatus.COMMITTED, DecisionEpisodeStatus.ANALYZING, DecisionEpisodeStatus.ABANDONED}
    ),
    DecisionEpisodeStatus.COMMITTED: frozenset(
        {DecisionEpisodeStatus.ACTING, DecisionEpisodeStatus.AWAITING_FEEDBACK, DecisionEpisodeStatus.ARCHIVED}
    ),
    DecisionEpisodeStatus.ACTING: frozenset(
        {DecisionEpisodeStatus.AWAITING_FEEDBACK, DecisionEpisodeStatus.ABANDONED}
    ),
    DecisionEpisodeStatus.AWAITING_FEEDBACK: frozenset(
        {DecisionEpisodeStatus.ACTING, DecisionEpisodeStatus.REFLECTED, DecisionEpisodeStatus.ARCHIVED}
    ),
    DecisionEpisodeStatus.REFLECTED: frozenset({DecisionEpisodeStatus.ARCHIVED}),
    DecisionEpisodeStatus.CANCELLED: frozenset({DecisionEpisodeStatus.ARCHIVED}),
    DecisionEpisodeStatus.ABANDONED: frozenset({DecisionEpisodeStatus.ARCHIVED}),
    DecisionEpisodeStatus.ARCHIVED: frozenset(),
}

REPORT_DRAFT_TRANSITIONS = {
    ReportDraftStatus.GENERATING: frozenset(
        {ReportDraftStatus.READY, ReportDraftStatus.INVALID, ReportDraftStatus.GENERATION_FAILED}
    ),
    ReportDraftStatus.READY: frozenset(
        {ReportDraftStatus.ACCEPTED, ReportDraftStatus.REJECTED, ReportDraftStatus.SUPERSEDED}
    ),
    ReportDraftStatus.GENERATION_FAILED: frozenset({ReportDraftStatus.GENERATING}),
    ReportDraftStatus.INVALID: frozenset({ReportDraftStatus.GENERATING, ReportDraftStatus.SUPERSEDED}),
    ReportDraftStatus.ACCEPTED: frozenset({ReportDraftStatus.SUPERSEDED}),
    ReportDraftStatus.REJECTED: frozenset({ReportDraftStatus.SUPERSEDED}),
    ReportDraftStatus.SUPERSEDED: frozenset(),
}

ACTION_PLAN_TRANSITIONS = {
    ActionPlanStatus.DRAFT: frozenset({ActionPlanStatus.CONFIRMED, ActionPlanStatus.ABANDONED}),
    ActionPlanStatus.CONFIRMED: frozenset(
        {ActionPlanStatus.IN_PROGRESS, ActionPlanStatus.ABANDONED, ActionPlanStatus.SUPERSEDED}
    ),
    ActionPlanStatus.IN_PROGRESS: frozenset(
        {ActionPlanStatus.COMPLETED, ActionPlanStatus.ABANDONED, ActionPlanStatus.SUPERSEDED}
    ),
    ActionPlanStatus.COMPLETED: frozenset(),
    ActionPlanStatus.ABANDONED: frozenset(),
    ActionPlanStatus.SUPERSEDED: frozenset(),
}

FEEDBACK_TRANSITIONS = {
    FeedbackStatus.DRAFT: frozenset({FeedbackStatus.PENDING_CONFIRMATION, FeedbackStatus.ARCHIVED}),
    FeedbackStatus.PENDING_CONFIRMATION: frozenset(
        {FeedbackStatus.DRAFT, FeedbackStatus.CONFIRMED, FeedbackStatus.ARCHIVED}
    ),
    FeedbackStatus.CONFIRMED: frozenset({FeedbackStatus.CORRECTED, FeedbackStatus.ARCHIVED}),
    FeedbackStatus.CORRECTED: frozenset({FeedbackStatus.ARCHIVED}),
    FeedbackStatus.ARCHIVED: frozenset(),
}

MEMORY_CANDIDATE_TRANSITIONS = {
    MemoryCandidateStatus.SUGGESTED: frozenset(
        {MemoryCandidateStatus.EDITED, MemoryCandidateStatus.CONFIRMED,
         MemoryCandidateStatus.REJECTED, MemoryCandidateStatus.EXPIRED}
    ),
    MemoryCandidateStatus.EDITED: frozenset(
        {MemoryCandidateStatus.CONFIRMED, MemoryCandidateStatus.REJECTED,
         MemoryCandidateStatus.EXPIRED}
    ),
    MemoryCandidateStatus.CONFIRMED: frozenset(),
    MemoryCandidateStatus.REJECTED: frozenset(),
    MemoryCandidateStatus.EXPIRED: frozenset(),
}

DECISION_MEMORY_TRANSITIONS = {
    DecisionMemoryStatus.ACTIVE: frozenset(
        {DecisionMemoryStatus.NEEDS_REVIEW, DecisionMemoryStatus.SUPERSEDED,
         DecisionMemoryStatus.DISABLED, DecisionMemoryStatus.ARCHIVED,
         DecisionMemoryStatus.DELETED}
    ),
    DecisionMemoryStatus.NEEDS_REVIEW: frozenset(
        {DecisionMemoryStatus.ACTIVE, DecisionMemoryStatus.SUPERSEDED,
         DecisionMemoryStatus.DISABLED, DecisionMemoryStatus.ARCHIVED,
         DecisionMemoryStatus.DELETED}
    ),
    DecisionMemoryStatus.DISABLED: frozenset(
        {DecisionMemoryStatus.ACTIVE, DecisionMemoryStatus.ARCHIVED, DecisionMemoryStatus.DELETED}
    ),
    DecisionMemoryStatus.SUPERSEDED: frozenset({DecisionMemoryStatus.ARCHIVED, DecisionMemoryStatus.DELETED}),
    DecisionMemoryStatus.ARCHIVED: frozenset({DecisionMemoryStatus.DELETED}),
    DecisionMemoryStatus.DELETED: frozenset(),
}
