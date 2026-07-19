"""Authenticated profile pipeline endpoints."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.profile_service import confirm_profile, get_profile, update_profile

router = APIRouter(prefix="/profile")


@router.get("", response_model=ProfileResponse)
async def read_profile(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ProfileResponse:
    return await get_profile(settings, user)


@router.put("", response_model=ProfileResponse)
async def save_profile(
    payload: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ProfileResponse:
    return await update_profile(settings, user, payload)


@router.post("/confirm", response_model=ProfileResponse)
async def confirm_current_profile(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ProfileResponse:
    return await confirm_profile(settings, user)
