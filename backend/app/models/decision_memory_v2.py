"""Memory Candidate and Decision Memory V2 domain models."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.models.v2_common import (
    DecisionMemoryStatus,
    EvidenceReferenceV2,
    MemoryCandidateStatus,
    MemoryType,
    V2DomainModel,
)


class MemoryCandidate(V2DomainModel):
    """Proposed memory that cannot be used as long-term context until confirmed."""

    decision_episode_id: UUID
    feedback_id: UUID | None = None
    candidate_type: MemoryType
    proposed_content: str = Field(min_length=1, max_length=5_000)
    rationale: str = Field(min_length=1, max_length=2_000)
    evidence: list[EvidenceReferenceV2] = Field(default_factory=list)
    applicable_domains: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    status: MemoryCandidateStatus = MemoryCandidateStatus.SUGGESTED
    proposed_expires_at: datetime | None = None
    reviewed_at: datetime | None = None


class DecisionMemory(V2DomainModel):
    """User-confirmed long-term decision experience available to retrieval."""

    source_candidate_id: UUID
    memory_type: MemoryType
    content: str = Field(min_length=1, max_length=5_000)
    applicable_domains: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReferenceV2] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    status: DecisionMemoryStatus = DecisionMemoryStatus.ACTIVE
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    review_after: datetime | None = None
    confirmed_at: datetime
    last_used_at: datetime | None = None
    usage_count: int = Field(default=0, ge=0)
    supersedes_memory_id: UUID | None = None

    @model_validator(mode="after")
    def require_confirmation(self) -> "DecisionMemory":
        if self.confirmed_at is None:
            raise ValueError("Decision Memory requires explicit user confirmation")
        return self
