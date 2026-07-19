"""Persist and reload decision cases, AI reports, and action plans via Supabase."""

from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.schemas.reflection import (
    AnalysisSection,
    DecisionReport,
    DecisionTimelineItem,
    SavedDecisionReport,
)


def _headers(settings: Settings, user: CurrentUser, *, return_row: bool = False) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_anon_key or "",
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json",
    }
    if return_row:
        headers["Prefer"] = "return=representation"
    return headers


def _saved_report(report_row: dict[str, Any], case_row: dict[str, Any]) -> SavedDecisionReport:
    report = DecisionReport.model_validate(report_row["content"])
    action_plan = AnalysisSection.model_validate(case_row.get("user_action") or report.action_plan)
    return SavedDecisionReport(
        id=report_row["id"],
        decision_case_id=case_row["id"],
        question=case_row["user_question"],
        report=report,
        action_plan=action_plan,
        model_name=report_row.get("model_name"),
        prompt_version=report_row.get("prompt_version"),
        created_at=report_row["created_at"],
    )


async def save_decision_report(
    settings: Settings,
    user: CurrentUser,
    question: str,
    report: DecisionReport,
    *,
    model_name: str,
    prompt_version: str,
) -> SavedDecisionReport:
    """Save the case first, then its complete AI report linked by reflection_id."""

    case_payload = {
        "user_id": str(user.id),
        "title": question[:200],
        "user_question": question,
        "ai_analysis": report.decision_recommendation.summary,
        "user_action": report.action_plan.model_dump(mode="json"),
        "status": "saved",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        case_response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/reflections",
            headers=_headers(settings, user, return_row=True),
            json=case_payload,
        )
        if case_response.status_code != 201 or not case_response.json():
            raise HTTPException(status_code=502, detail="Unable to save decision case")
        case_row = case_response.json()[0]

        report_response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/analysis_reports",
            headers=_headers(settings, user, return_row=True),
            json={
                "user_id": str(user.id),
                "reflection_id": case_row["id"],
                "content": report.model_dump(mode="json"),
                "model_name": model_name,
                "prompt_version": prompt_version,
            },
        )
        if report_response.status_code != 201 or not report_response.json():
            raise HTTPException(status_code=502, detail="Unable to save decision report")

    return _saved_report(report_response.json()[0], case_row)


async def get_decision_report(
    settings: Settings, user: CurrentUser, report_id: UUID
) -> SavedDecisionReport:
    """Reload one persisted report; RLS additionally enforces report ownership."""

    async with httpx.AsyncClient(timeout=10) as client:
        report_response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/analysis_reports",
            params={
                "id": f"eq.{report_id}",
                "user_id": f"eq.{user.id}",
                "select": "*",
            },
            headers=_headers(settings, user),
        )
        if report_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to load decision report")
        report_rows = report_response.json()
        if not report_rows:
            raise HTTPException(status_code=404, detail="Decision report not found")
        report_row = report_rows[0]

        case_response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/reflections",
            params={
                "id": f"eq.{report_row['reflection_id']}",
                "user_id": f"eq.{user.id}",
                "select": "*",
            },
            headers=_headers(settings, user),
        )
        if case_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to load decision case")
        case_rows = case_response.json()
        if not case_rows:
            raise HTTPException(status_code=404, detail="Decision case not found")

    return _saved_report(report_row, case_rows[0])


async def list_decision_timeline(
    settings: Settings, user: CurrentUser
) -> list[DecisionTimelineItem]:
    """Return only the authenticated user's reports, newest first."""

    async with httpx.AsyncClient(timeout=10) as client:
        report_response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/analysis_reports",
            params={
                "user_id": f"eq.{user.id}",
                "select": "id,reflection_id,content,created_at",
                "order": "created_at.desc,id.desc",
            },
            headers=_headers(settings, user),
        )
        if report_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to load decision timeline")
        report_rows = report_response.json()
        if not report_rows:
            return []

        case_ids = ",".join(str(row["reflection_id"]) for row in report_rows)
        case_response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/reflections",
            params={
                "id": f"in.({case_ids})",
                "user_id": f"eq.{user.id}",
                "select": "id,user_question",
            },
            headers=_headers(settings, user),
        )
        if case_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to load decision cases")
        cases = {str(row["id"]): row for row in case_response.json()}

    timeline: list[DecisionTimelineItem] = []
    for row in report_rows:
        case = cases.get(str(row["reflection_id"]))
        if case is None:
            continue
        report = DecisionReport.model_validate(row["content"])
        timeline.append(
            DecisionTimelineItem(
                id=row["id"],
                decision_case_id=row["reflection_id"],
                question=case["user_question"],
                decision_summary=report.decision_recommendation.summary,
                created_at=row["created_at"],
            )
        )
    return timeline
