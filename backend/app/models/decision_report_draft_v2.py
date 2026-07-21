"""AI-generated Decision Report Draft V2 domain model."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.v2_common import ReportDraftStatus, V2DomainModel


class ReportSectionV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=5_000)
    points: list[str] = Field(default_factory=list)


class DecisionOptionV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=300)
    benefits: list[str] = Field(default_factory=list)
    costs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunity_costs: list[str] = Field(default_factory=list)
    long_term_impacts: list[str] = Field(default_factory=list)
    reversibility: str | None = Field(default=None, max_length=1_000)


class DecisionReportDraft(V2DomainModel):
    """Reviewable AI analysis; never represents the user's final decision."""

    decision_episode_id: UUID
    version: int = Field(default=1, ge=1)
    status: ReportDraftStatus = ReportDraftStatus.GENERATING
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
    context_snapshot: dict[str, Any] | None = None
    reviewed_at: datetime | None = None
