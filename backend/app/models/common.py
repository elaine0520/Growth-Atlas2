"""Shared value objects and enums for Growth Atlas domain models."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class RecordStatus(StrEnum):
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    SAVED = "saved"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ContentSource(StrEnum):
    USER_INPUT = "user_input"
    USER_CONFIRMED = "user_confirmed"
    AI_GENERATED = "ai_generated"
    HISTORICAL_SUMMARY = "historical_summary"


class ConfirmationStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class GrowthDimension(StrEnum):
    SELF_AWARENESS = "self_awareness"
    EMOTIONAL_MANAGEMENT = "emotional_management"
    DECISION_MAKING = "decision_making"
    EXECUTION = "execution"
    RELATIONSHIPS = "relationships"
    LEARNING_GROWTH = "learning_growth"


class ScoreStatus(StrEnum):
    INSUFFICIENT_DATA = "insufficient_data"
    PRELIMINARY_OBSERVATION = "preliminary_observation"
    EVIDENCE_SUPPORTED = "evidence_supported"


class GrowthTrend(StrEnum):
    NO_TREND = "no_trend"
    IMPROVING = "improving"
    STABLE = "stable"
    FLUCTUATING = "fluctuating"
    NEEDS_ATTENTION = "needs_attention"


class DomainModel(BaseModel):
    """Base class shared by local, persistence-agnostic domain models."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    status: RecordStatus = RecordStatus.DRAFT
    source: ContentSource = ContentSource.USER_INPUT
    confirmation_status: ConfirmationStatus = ConfirmationStatus.UNCONFIRMED
    is_deleted: bool = False


class EvidenceReference(BaseModel):
    """Traceable source used by an AI analysis or growth assessment."""

    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(min_length=1, max_length=50)
    source_id: UUID
    note: str | None = Field(default=None, max_length=500)

