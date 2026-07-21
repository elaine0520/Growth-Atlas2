"""Profile persistence through Supabase REST with the user's JWT and RLS."""

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.schemas.profile import ProfileResponse, ProfileUpdate


def _headers(settings: Settings, user: CurrentUser, *, return_row: bool = False) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_anon_key or "",
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json",
    }
    if return_row:
        headers["Prefer"] = "return=representation"
    return headers


async def _create_missing_profile(
    client: httpx.AsyncClient, settings: Settings, user: CurrentUser
) -> ProfileResponse:
    """Recover accounts whose Auth user exists but profile trigger did not run."""
    response = await client.post(
        f"{settings.supabase_url.rstrip('/')}/rest/v1/profiles",
        params={"on_conflict": "id"},
        headers={
            **_headers(settings, user, return_row=True),
            "Prefer": "resolution=merge-duplicates,return=representation",
        },
        json={"id": str(user.id)},
    )
    if response.status_code not in {200, 201} or not response.json():
        raise HTTPException(status_code=502, detail="Unable to initialize profile")
    return _to_response(response.json()[0])


def _to_response(row: dict[str, Any]) -> ProfileResponse:
    return ProfileResponse(
        id=row["id"],
        user_info={
            "nickname": row.get("nickname"),
            "age_range": row.get("age_range"),
            "life_stage": row.get("life_stage"),
            "background": row.get("background"),
            "locale": row.get("locale", "zh-CN"),
            "timezone": row.get("timezone", "Asia/Shanghai"),
        },
        current_context=row.get("current_context"),
        pressure_sources=row.get("pressure_sources", []),
        short_term_goals=row.get("short_term_goals", []),
        long_term_goals=row.get("long_term_goals", []),
        values=row.get("values_list", []),
        self_description=row.get("self_description", []),
        status=row["status"],
        version=row["version"],
        confirmed_at=row.get("confirmed_at"),
        last_reviewed_at=row.get("last_reviewed_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _db_payload(payload: ProfileUpdate) -> dict[str, Any]:
    info = payload.user_info
    return {
        "nickname": info.nickname,
        "age_range": info.age_range,
        "life_stage": info.life_stage,
        "background": info.background,
        "locale": info.locale,
        "timezone": info.timezone,
        "current_context": payload.current_context,
        "pressure_sources": payload.pressure_sources,
        "short_term_goals": payload.short_term_goals,
        "long_term_goals": payload.long_term_goals,
        "values_list": payload.values,
        "self_description": payload.self_description,
    }


async def get_profile(settings: Settings, user: CurrentUser) -> ProfileResponse:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/profiles",
            params={"id": f"eq.{user.id}", "select": "*"},
            headers=_headers(settings, user),
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to load profile")
        rows = response.json()
        if not rows:
            return await _create_missing_profile(client, settings, user)
        return _to_response(rows[0])


async def update_profile(
    settings: Settings, user: CurrentUser, payload: ProfileUpdate
) -> ProfileResponse:
    body = {**_db_payload(payload), "status": "draft", "confirmed_at": None}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.patch(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/profiles",
            params={"id": f"eq.{user.id}"},
            headers=_headers(settings, user, return_row=True),
            json=body,
        )
    if response.status_code != 200 or not response.json():
        raise HTTPException(status_code=502, detail="Unable to save profile")
    return _to_response(response.json()[0])


async def confirm_profile(settings: Settings, user: CurrentUser) -> ProfileResponse:
    current = await get_profile(settings, user)
    has_goal = bool(current.short_term_goals or current.long_term_goals)
    if not current.user_info.life_stage or not current.current_context or not has_goal or not current.values:
        raise HTTPException(
            status_code=409,
            detail="Complete life stage, current context, at least one goal, and values before confirming",
        )
    confirmed_at = datetime.now(timezone.utc).isoformat()
    body = {
        "status": "confirmed",
        "confirmed_at": confirmed_at,
        "last_reviewed_at": confirmed_at,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.patch(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/profiles",
            params={"id": f"eq.{user.id}"},
            headers=_headers(settings, user, return_row=True),
            json=body,
        )
    if response.status_code != 200 or not response.json():
        raise HTTPException(status_code=502, detail="Unable to confirm profile")
    return _to_response(response.json()[0])
