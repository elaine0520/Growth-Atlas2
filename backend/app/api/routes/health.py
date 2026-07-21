from fastapi import APIRouter, Depends, Response, status

from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health", summary="Check API availability")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Report runtime dependency configuration")
async def readiness_check(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    dependencies = {
        "ai": bool(settings.kimi_api_key),
        "supabase": settings.supabase_configured,
    }
    issues = settings.production_issues
    ready = all(dependencies.values()) and not issues
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "degraded",
        "environment": settings.app_env,
        "dependencies": dependencies,
        "configuration_issues": issues,
    }
