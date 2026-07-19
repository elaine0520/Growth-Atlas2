"""Reflection and persisted decision-report API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.reflection import ActionPlan


class ReflectionCreate(BaseModel):
    """Fields accepted when the frontend saves a reflection."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    title: str = Field(min_length=1, max_length=200)
    user_question: str = Field(min_length=1, max_length=10_000)
    desired_outcome: str | None = Field(default=None, max_length=2_000)
    confirmed_facts: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    emotions_and_needs: list[str] = Field(default_factory=list)
    user_insights: list[str] = Field(default_factory=list)
    action_plan: ActionPlan | None = None


class DecisionAnalysisRequest(BaseModel):
    """A single decision question sent to the AI decision advisor."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=800)


class AnalysisSection(BaseModel):
    summary: str
    points: list[str]


class DecisionReport(BaseModel):
    """Structured Goal → Feedback decision report rendered by Reflection."""

    goal_clarification: AnalysisSection
    facts_analysis: AnalysisSection
    constraints_analysis: AnalysisSection
    options_comparison: AnalysisSection
    decision_recommendation: AnalysisSection
    action_plan: AnalysisSection


class SavedDecisionReport(BaseModel):
    """A decision case and its AI report after they have been persisted."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    decision_case_id: UUID
    question: str
    report: DecisionReport
    action_plan: AnalysisSection
    model_name: str | None = None
    prompt_version: str | None = None
    created_at: datetime


class DecisionTimelineItem(BaseModel):
    """Compact report metadata used by the current user's decision history."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    decision_case_id: UUID
    question: str
    decision_summary: str
    created_at: datetime
