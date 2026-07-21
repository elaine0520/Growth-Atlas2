"""Assemble the V2 lifecycle timeline without scores or inferred personality."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.schemas.growth_map import (
    ConfirmedExperience,
    DecisionTimelineEntry,
    GrowthMapResponse,
    TimelineActionItem,
    TimelineActionPlan,
    TimelineFeedback,
)


async def get_growth_map(
    settings: Settings,
    user: CurrentUser,
) -> GrowthMapResponse:
    base = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_anon_key or "",
        "Authorization": f"Bearer {user.access_token}",
    }
    queries = [
        ("decision_episodes", {"user_id": f"eq.{user.id}", "select": "*", "order": "created_at.asc"}),
        ("action_plans", {"user_id": f"eq.{user.id}", "select": "*", "order": "created_at.asc"}),
        ("action_items", {"user_id": f"eq.{user.id}", "select": "*", "order": "sequence.asc"}),
        ("feedback_entries", {
            "user_id": f"eq.{user.id}", "status": "in.(confirmed,corrected)",
            "select": "*", "order": "created_at.asc",
        }),
        ("memory_candidates", {
            "user_id": f"eq.{user.id}", "status": "eq.confirmed", "select": "*",
        }),
        ("decision_memories", {
            "user_id": f"eq.{user.id}", "status": "in.(active,disabled,needs_review)",
            "select": "*", "order": "confirmed_at.asc",
        }),
    ]
    data: dict[str, list[dict[str, Any]]] = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for table, params in queries:
            response = await client.get(
                f"{base}/rest/v1/{table}", params=params, headers=headers,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Unable to load Growth Map")
            data[table] = response.json()
    return assemble_growth_map(
        episodes=data["decision_episodes"],
        plans=data["action_plans"],
        action_items=data["action_items"],
        feedback=data["feedback_entries"],
        candidates=data["memory_candidates"],
        memories=data["decision_memories"],
    )


def assemble_growth_map(
    *,
    episodes: list[dict[str, Any]],
    plans: list[dict[str, Any]],
    action_items: list[dict[str, Any]],
    feedback: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    memories: list[dict[str, Any]],
) -> GrowthMapResponse:
    items_by_plan: dict[str, list[TimelineActionItem]] = {}
    for row in action_items:
        items_by_plan.setdefault(str(row["action_plan_id"]), []).append(
            TimelineActionItem(
                id=row["id"], description=row["description"], status=row["status"],
                completed_at=row.get("completed_at"),
            )
        )

    plans_by_episode: dict[str, list[dict[str, Any]]] = {}
    for row in plans:
        plans_by_episode.setdefault(str(row["decision_episode_id"]), []).append(row)

    feedback_by_episode: dict[str, list[TimelineFeedback]] = {}
    for row in feedback:
        feedback_by_episode.setdefault(str(row["decision_episode_id"]), []).append(
            TimelineFeedback(
                id=row["id"], actual_outcome=row.get("actual_outcome"),
                expected_vs_actual=row.get("expected_vs_actual"),
                lessons_learned=row.get("lessons_learned", []),
                confirmed_at=row.get("confirmed_at"),
            )
        )

    candidate_episode = {
        str(row["id"]): UUID(str(row["decision_episode_id"])) for row in candidates
    }
    experiences: list[ConfirmedExperience] = []
    experiences_by_episode: dict[str, list[ConfirmedExperience]] = {}
    for row in memories:
        source_candidate_id = str(row["source_candidate_id"])
        source_episode_id = candidate_episode.get(source_candidate_id)
        if source_episode_id is None:
            continue
        experience = ConfirmedExperience(
            id=row["id"], source_candidate_id=source_candidate_id,
            source_episode_id=source_episode_id, memory_type=row["memory_type"],
            content=row["content"], status=row["status"],
            applicable_domains=row.get("applicable_domains", []),
            confirmed_at=row["confirmed_at"],
        )
        experiences.append(experience)
        experiences_by_episode.setdefault(str(source_episode_id), []).append(experience)

    timeline: list[DecisionTimelineEntry] = []
    for row in episodes:
        episode_id = str(row["id"])
        episode_plans = plans_by_episode.get(episode_id, [])
        latest_plan_row = episode_plans[-1] if episode_plans else None
        action_plan = None
        if latest_plan_row:
            plan_id = str(latest_plan_row["id"])
            action_plan = TimelineActionPlan(
                id=latest_plan_row["id"], objective=latest_plan_row["objective"],
                status=latest_plan_row["status"],
                success_criteria=latest_plan_row.get("success_criteria"),
                confirmed_at=latest_plan_row.get("confirmed_at"),
                actions=items_by_plan.get(plan_id, []),
            )
        timeline.append(DecisionTimelineEntry(
            id=row["id"], title=row["title"],
            decision_question=row["decision_question"], domain=row.get("domain"),
            status=row["status"], final_decision=row.get("final_decision"),
            decision_rationale=row.get("decision_rationale"),
            created_at=row["created_at"], committed_at=row.get("committed_at"),
            closed_at=row.get("closed_at"), action_plan=action_plan,
            feedback=feedback_by_episode.get(episode_id, []),
            confirmed_experiences=experiences_by_episode.get(episode_id, []),
        ))

    return GrowthMapResponse(
        timeline=timeline,
        confirmed_experiences=experiences,
        generated_at=datetime.now(timezone.utc),
    )
