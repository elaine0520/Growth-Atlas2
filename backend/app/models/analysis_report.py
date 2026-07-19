"""AI analysis report and qualitative growth assessment models."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import (
    DomainModel,
    EvidenceReference,
    GrowthDimension,
    GrowthTrend,
    ScoreStatus,
)


class GrowthScore(BaseModel):
    """Evidence-backed score; numeric value stays optional by design."""

    model_config = ConfigDict(extra="forbid")

    dimension: GrowthDimension
    status: ScoreStatus = ScoreStatus.INSUFFICIENT_DATA
    trend: GrowthTrend = GrowthTrend.NO_TREND
    numeric_score: float | None = Field(default=None, ge=0, le=100)
    observed_strengths: list[str] = Field(default_factory=list)
    observed_changes: list[str] = Field(default_factory=list)
    patterns_to_watch: list[str] = Field(default_factory=list)
    next_stage_suggestions: list[str] = Field(default_factory=list)
    confidence_note: str | None = Field(default=None, max_length=2_000)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class AnalysisReport(DomainModel):
    """A traceable AI result for one reflection or a reporting period."""

    period_start: date | None = None
    period_end: date | None = None
    problem_summary: str = Field(min_length=1, max_length=3_000)
    ai_analysis: str = Field(min_length=1, max_length=15_000)
    key_insights: list[str] = Field(default_factory=list)
    action_suggestions: list[str] = Field(default_factory=list)
    growth_scores: list[GrowthScore] = Field(default_factory=list, max_length=6)
    limitations: list[str] = Field(default_factory=list)
    model_name: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=50)
    evidence: list[EvidenceReference] = Field(default_factory=list)

