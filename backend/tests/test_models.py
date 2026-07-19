"""Tests for the persistence-agnostic domain models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import AnalysisReport, GrowthScore, Reflection, UserProfile
from app.models.common import GrowthDimension


def test_profile_uses_independent_collection_defaults() -> None:
    first = UserProfile(user_id=uuid4(), long_term_goals=["完成学业规划"])
    second = UserProfile(user_id=uuid4())

    first.values.append("自主")

    assert second.values == []
    assert first.long_term_goals == ["完成学业规划"]


def test_reflection_requires_a_question_and_title() -> None:
    with pytest.raises(ValidationError):
        Reflection(user_id=uuid4(), title="", user_question="")


def test_growth_score_rejects_out_of_range_numeric_value() -> None:
    with pytest.raises(ValidationError):
        GrowthScore(dimension=GrowthDimension.EXECUTION, numeric_score=101)


def test_analysis_report_accepts_qualitative_growth_score() -> None:
    report = AnalysisReport(
        user_id=uuid4(),
        problem_summary="最近总是拖延重要任务",
        ai_analysis="现有记录显示启动条件不够明确。",
        action_suggestions=["把下一步缩小为十分钟内可完成的动作"],
        growth_scores=[GrowthScore(dimension=GrowthDimension.EXECUTION)],
    )

    assert report.growth_scores[0].numeric_score is None
