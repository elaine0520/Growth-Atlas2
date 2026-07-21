"""Decision lifecycle Timeline and non-scoring Growth Map endpoints."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.schemas.growth_map import DecisionTimelineEntry, GrowthMapResponse
from app.services.growth_map_service import get_growth_map

router = APIRouter()


@router.get("/decision-timeline", response_model=list[DecisionTimelineEntry])
async def read_decision_timeline(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[DecisionTimelineEntry]:
    return (await get_growth_map(settings, user)).timeline


@router.get("/growth-map", response_model=GrowthMapResponse)
async def read_growth_map(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GrowthMapResponse:
    return await get_growth_map(settings, user)
