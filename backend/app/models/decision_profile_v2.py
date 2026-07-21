"""Personal Decision Profile V2 domain model."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.v2_common import EvidenceReferenceV2, ProfileStatus, V2DomainModel


class ProfileItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=2_000)
    evidence: list[EvidenceReferenceV2] = Field(default_factory=list)
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    confirmed_at: datetime | None = None


class StableProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    long_term_goals: list[ProfileItem] = Field(default_factory=list)
    core_values: list[ProfileItem] = Field(default_factory=list)
    long_term_directions: list[ProfileItem] = Field(default_factory=list)
    important_principles: list[ProfileItem] = Field(default_factory=list)


class DynamicContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_stage: ProfileItem | None = None
    current_environment: ProfileItem | None = None
    current_projects: list[ProfileItem] = Field(default_factory=list)
    current_pressures: list[ProfileItem] = Field(default_factory=list)
    current_resources: list[ProfileItem] = Field(default_factory=list)
    current_constraints: list[ProfileItem] = Field(default_factory=list)
    effective_at: datetime | None = None
    review_after: datetime | None = None


class DecisionStyleObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str = Field(min_length=1, max_length=100)
    observation: str = Field(min_length=1, max_length=2_000)
    supporting_episode_ids: list[UUID] = Field(default_factory=list)
    evidence_count: int = Field(default=0, ge=0)
    confidence: float = Field(default=0, ge=0, le=1)
    user_confirmed: bool = False
    confirmed_at: datetime | None = None
    valid_until: datetime | None = None


class PersonalDecisionProfile(V2DomainModel):
    """Versioned, user-controlled context used to support decisions."""

    status: ProfileStatus = ProfileStatus.DRAFT
    version: int = Field(default=1, ge=1)
    stable_profile: StableProfile = Field(default_factory=StableProfile)
    dynamic_context: DynamicContext = Field(default_factory=DynamicContext)
    decision_style: list[DecisionStyleObservation] = Field(default_factory=list)
    confirmed_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    supersedes_profile_id: UUID | None = None
