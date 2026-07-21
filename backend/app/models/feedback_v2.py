"""Decision Feedback V2 domain model."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.v2_common import FeedbackStatus, FeedbackType, V2DomainModel


class FeedbackV2(V2DomainModel):
    """User-confirmed evidence about action, outcome, and learning."""

    decision_episode_id: UUID
    action_plan_id: UUID | None = None
    feedback_type: FeedbackType
    status: FeedbackStatus = FeedbackStatus.DRAFT
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
    confirmed_at: datetime | None = None
    corrects_feedback_id: UUID | None = None
