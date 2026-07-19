"""Reflection model for one structured user question."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import DomainModel, EvidenceReference


class ActionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=2_000)
    target_time: datetime | None = None
    minimum_success_criteria: str | None = Field(default=None, max_length=1_000)
    obstacles: list[str] = Field(default_factory=list)
    fallback_plan: str | None = Field(default=None, max_length=1_000)
    user_confirmed: bool = False


class FollowUpReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual_action: str = Field(min_length=1, max_length=2_000)
    outcome: str | None = Field(default=None, max_length=2_000)
    changes: str | None = Field(default=None, max_length=2_000)
    reusable_insight: str | None = Field(default=None, max_length=2_000)
    reviewed_at: datetime


class Reflection(DomainModel):
    """A question and its reflection-to-action lifecycle."""

    title: str = Field(min_length=1, max_length=200)
    user_question: str = Field(min_length=1, max_length=10_000)
    desired_outcome: str | None = Field(default=None, max_length=2_000)
    confirmed_facts: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    emotions_and_needs: list[str] = Field(default_factory=list)
    user_insights: list[str] = Field(default_factory=list)
    ai_analysis: str | None = Field(default=None, max_length=10_000)
    ai_suggestions: list[str] = Field(default_factory=list)
    action_plan: ActionPlan | None = None
    follow_ups: list[FollowUpReview] = Field(default_factory=list)
    conversation_id: UUID | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)

