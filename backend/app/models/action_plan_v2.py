"""Action Plan V2 domain model."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.models.v2_common import ActionItemStatus, ActionPlanStatus, V2DomainModel


class ActionItemV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    description: str = Field(min_length=1, max_length=2_000)
    sequence: int = Field(ge=1)
    due_at: datetime | None = None
    status: ActionItemStatus = ActionItemStatus.PENDING
    completion_note: str | None = Field(default=None, max_length=2_000)
    completed_at: datetime | None = None


class ActionPlanV2(V2DomainModel):
    """A user-editable plan that becomes official only after confirmation."""

    decision_episode_id: UUID
    source_report_draft_id: UUID | None = None
    status: ActionPlanStatus = ActionPlanStatus.DRAFT
    objective: str = Field(min_length=1, max_length=3_000)
    actions: list[ActionItemV2] = Field(default_factory=list)
    success_criteria: str | None = Field(default=None, max_length=2_000)
    key_assumptions: list[str] = Field(default_factory=list)
    major_obstacles: list[str] = Field(default_factory=list)
    fallback_plan: str | None = Field(default=None, max_length=2_000)
    review_at: datetime | None = None
    confirmed_at: datetime | None = None
