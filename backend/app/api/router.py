from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.profile import router as profile_router
from app.api.routes.reflection import router as reflection_router
from app.api.routes.report import router as report_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(profile_router, tags=["profile"])
api_router.include_router(reflection_router, tags=["reflection"])
api_router.include_router(report_router, tags=["report"])
