from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.growth_map import router as growth_map_router
from app.api.routes.memory import router as memory_router
from app.api.routes.action_feedback import router as action_feedback_router
from app.api.routes.decision_episode import router as decision_episode_router
from app.api.routes.profile import router as profile_router
from app.api.routes.reflection import router as reflection_router
from app.api.routes.report import router as report_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(growth_map_router, tags=["growth-map"])
api_router.include_router(memory_router, tags=["memory"])
api_router.include_router(action_feedback_router, tags=["action-feedback"])
api_router.include_router(decision_episode_router, tags=["decision-episode"])
api_router.include_router(profile_router, tags=["profile"])
api_router.include_router(reflection_router, tags=["reflection"])
api_router.include_router(report_router, tags=["report"])
