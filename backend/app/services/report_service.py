"""Temporary growth report service returning deterministic mock data."""

from datetime import date, timedelta
from uuid import UUID

from app.models.analysis_report import AnalysisReport, GrowthScore
from app.models.common import (
    ConfirmationStatus,
    ContentSource,
    GrowthDimension,
    RecordStatus,
)


def get_growth_report(user_id: UUID) -> AnalysisReport:
    """Build a six-dimension report that explicitly marks limited evidence."""

    today = date.today()
    dimensions = list(GrowthDimension)
    return AnalysisReport(
        user_id=user_id,
        period_start=today - timedelta(days=30),
        period_end=today,
        problem_summary="阶段性成长报告（模拟数据）",
        ai_analysis="当前尚未连接数据库，以下内容仅用于前后端联调。",
        key_insights=["已建立基础成长档案结构。", "成长记录数量不足，暂不形成确定性结论。"],
        action_suggestions=["继续记录真实问题、行动与后续回顾。"],
        growth_scores=[
            GrowthScore(
                dimension=dimension,
                confidence_note="模拟数据：当前没有足够记录支持趋势判断。",
            )
            for dimension in dimensions
        ],
        limitations=["未连接数据库。", "未调用 OpenAI API。", "当前报告为模拟数据。"],
        status=RecordStatus.PENDING_CONFIRMATION,
        source=ContentSource.HISTORICAL_SUMMARY,
        confirmation_status=ConfirmationStatus.UNCONFIRMED,
    )
