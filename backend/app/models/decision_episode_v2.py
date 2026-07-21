"""Decision Episode V2 domain model."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.v2_common import DecisionEpisodeStatus, EvidenceReferenceV2, V2DomainModel


class DecisionContextSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: UUID | None = None
    profile_version: int | None = Field(default=None, ge=1)
    selected_profile_items: list[str] = Field(default_factory=list)
    selected_memory_ids: list[UUID] = Field(default_factory=list)
    selected_historical_episode_ids: list[UUID] = Field(default_factory=list)
    memory_relevance: dict[str, float] = Field(default_factory=dict)
    historical_episode_relevance: dict[str, float] = Field(default_factory=dict)
    retrieval_version: str | None = Field(default=None, max_length=50)
    current_user_input: str = Field(min_length=1, max_length=10_000)
    context_builder_version: str = Field(min_length=1, max_length=50)
    generated_at: datetime


class DecisionEpisode(V2DomainModel):
    """Aggregate root for one important decision and its learning lifecycle."""

    title: str = Field(min_length=1, max_length=200)
    decision_question: str = Field(min_length=3, max_length=10_000)
    domain: str | None = Field(default=None, max_length=100)
    importance: int | None = Field(default=None, ge=1, le=5)
    background: str | None = Field(default=None, max_length=5_000)
    context_snapshot: DecisionContextSnapshot | None = None
    goal: str | None = Field(default=None, max_length=3_000)
    values: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    final_decision: str | None = Field(default=None, max_length=5_000)
    decision_rationale: str | None = Field(default=None, max_length=5_000)
    evidence: list[EvidenceReferenceV2] = Field(default_factory=list)
    status: DecisionEpisodeStatus = DecisionEpisodeStatus.CAPTURING
    profile_version_id: UUID | None = None
    profile_id: UUID | None = None
    profile_version: int | None = Field(default=None, ge=1)
    confirmed_from_draft_id: UUID | None = None
    committed_at: datetime | None = None
    closed_at: datetime | None = None
