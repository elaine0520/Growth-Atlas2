"""Growth report endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.models.analysis_report import AnalysisReport
from app.services.report_service import get_growth_report

router = APIRouter()
MOCK_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@router.get("/report", response_model=AnalysisReport)
async def get_report(
    user_id: UUID = Query(MOCK_USER_ID, description="User whose report is requested"),
) -> AnalysisReport:
    return get_growth_report(user_id)
