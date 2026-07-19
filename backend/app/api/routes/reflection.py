"""Reflection endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from openai import APIError

from app.core.auth import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.models.reflection import Reflection
from app.schemas.reflection import (
    DecisionAnalysisRequest,
    DecisionTimelineItem,
    ReflectionCreate,
    SavedDecisionReport,
)
from app.services.ai_analysis_service import AIAnalysisService
from app.services.decision_report_service import (
    get_decision_report,
    list_decision_timeline,
    save_decision_report,
)
from app.services.profile_service import get_profile
from app.services.reflection_service import create_reflection

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/reflection", response_model=Reflection, status_code=status.HTTP_201_CREATED)
async def post_reflection(payload: ReflectionCreate) -> Reflection:
    return create_reflection(payload)


@router.post("/reflection/analyze", response_model=SavedDecisionReport)
async def analyze_reflection(
    payload: DecisionAnalysisRequest,
    settings: Settings = Depends(get_settings),
    user: CurrentUser = Depends(get_current_user),
) -> SavedDecisionReport:
    try:
        service = AIAnalysisService(settings)
        profile = await get_profile(settings, user)
        report = await service.analyze(payload.question, profile)
        return await save_decision_report(
            settings,
            user,
            payload.question,
            report,
            model_name=service.model_name,
            prompt_version=service.prompt_version,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务尚未配置，请设置 KIMI_API_KEY。",
        ) from exc
    except (APIError, RuntimeError) as exc:
        logger.exception("Decision analysis failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 分析暂时不可用，请稍后重试。",
        ) from exc


@router.get("/reflection/timeline", response_model=list[DecisionTimelineItem])
async def read_decision_timeline(
    settings: Settings = Depends(get_settings),
    user: CurrentUser = Depends(get_current_user),
) -> list[DecisionTimelineItem]:
    return await list_decision_timeline(settings, user)


@router.get("/reflection/reports/{report_id}", response_model=SavedDecisionReport)
async def read_decision_report(
    report_id: UUID,
    settings: Settings = Depends(get_settings),
    user: CurrentUser = Depends(get_current_user),
) -> SavedDecisionReport:
    return await get_decision_report(settings, user, report_id)
