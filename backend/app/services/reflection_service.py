"""Temporary reflection service without database or AI dependencies."""

from app.models.common import ConfirmationStatus, ContentSource, RecordStatus
from app.models.reflection import Reflection
from app.schemas.reflection import ReflectionCreate


def create_reflection(payload: ReflectionCreate) -> Reflection:
    """Return a saved reflection with clearly identified mock analysis."""

    return Reflection(
        **payload.model_dump(),
        ai_analysis="模拟分析：当前接口尚未接入 AI 服务。",
        ai_suggestions=["将下一步行动拆分为一个可在短时间内完成的小步骤。"],
        status=RecordStatus.SAVED,
        source=ContentSource.USER_INPUT,
        confirmation_status=ConfirmationStatus.CONFIRMED,
    )
