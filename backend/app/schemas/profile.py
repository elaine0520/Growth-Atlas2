"""Profile API schemas built from the existing domain value objects."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.user_profile import UserInfo


class ProfileUpdate(BaseModel):
    """Editable user-owned profile fields; identity comes from the access token."""

    model_config = ConfigDict(extra="forbid")

    user_info: UserInfo = Field(default_factory=UserInfo)
    current_context: str | None = Field(default=None, max_length=2_000)
    pressure_sources: list[str] = Field(default_factory=list)
    short_term_goals: list[str] = Field(default_factory=list)
    long_term_goals: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    self_description: list[str] = Field(default_factory=list)


class ProfileResponse(ProfileUpdate):
    id: UUID
    status: Literal["draft", "pending_confirmation", "confirmed", "archived"]
    version: int
    confirmed_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
