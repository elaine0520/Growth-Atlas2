"""User growth profile model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import DomainModel


class UserInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nickname: str | None = Field(default=None, max_length=80)
    age_range: str | None = Field(default=None, max_length=50)
    life_stage: str | None = Field(default=None, max_length=100)
    background: str | None = Field(default=None, max_length=2_000)
    locale: str = Field(default="zh-CN", max_length=20)
    timezone: str = Field(default="Asia/Shanghai", max_length=50)


class UserProfile(DomainModel):
    """User-confirmed long-term context used for personalized analysis."""

    user_info: UserInfo = Field(default_factory=UserInfo)
    current_context: str | None = Field(default=None, max_length=2_000)
    pressure_sources: list[str] = Field(default_factory=list)
    short_term_goals: list[str] = Field(default_factory=list)
    long_term_goals: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    self_description: list[str] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    confirmed_at: datetime | None = None
    last_reviewed_at: datetime | None = None

