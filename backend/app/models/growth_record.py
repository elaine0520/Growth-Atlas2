"""Saved growth record model."""

from uuid import UUID

from pydantic import Field

from app.models.common import DomainModel
from app.models.reflection import ActionPlan, FollowUpReview


class GrowthRecord(DomainModel):
    """Minimal, user-approved record distilled from a reflection."""

    reflection_id: UUID
    analysis_report_id: UUID | None = None
    problem_summary: str = Field(min_length=1, max_length=3_000)
    key_analysis: list[str] = Field(default_factory=list)
    personal_insights: list[str] = Field(default_factory=list)
    confirmed_action_plan: ActionPlan
    follow_ups: list[FollowUpReview] = Field(default_factory=list)
    growth_score_snapshot: dict[str, float | str | None] = Field(default_factory=dict)

