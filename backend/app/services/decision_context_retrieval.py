"""Retrieve minimal, relevant, user-confirmed context for a Decision Episode."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.models.decision_episode_v2 import DecisionEpisode
from app.models.decision_memory_v2 import DecisionMemory
from app.models.decision_profile_v2 import PersonalDecisionProfile
from app.schemas.profile import ProfileResponse
from app.services.profile_service import get_profile


ConfirmedProfile = ProfileResponse | PersonalDecisionProfile


MIN_MEMORY_CONFIDENCE = 0.5
MAX_MEMORIES = 5
MAX_HISTORICAL_EPISODES = 3
RETRIEVAL_VERSION = "decision-context-retrieval-v2"
STOP_TOKENS = {
    "是否", "应该", "可以", "一个", "这个", "那个", "什么", "怎么",
    "如何", "决定", "选择", "需要", "还是", "以及", "the", "and", "or",
}


@dataclass(frozen=True)
class RelevantMemory:
    memory: DecisionMemory
    relevance: float


@dataclass(frozen=True)
class HistoricalEpisodeContext:
    id: UUID
    domain: str | None
    decision_question: str
    final_decision: str
    decision_rationale: str | None
    closed_at: datetime | None
    relevance: float


@dataclass(frozen=True)
class RetrievedDecisionContext:
    profile: ConfirmedProfile | None = None
    memories: list[RelevantMemory] = field(default_factory=list)
    historical_episodes: list[HistoricalEpisodeContext] = field(default_factory=list)
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = RETRIEVAL_VERSION


class DecisionContextRetrievalService:
    """Apply ownership, confirmation, validity, confidence, and relevance filters."""

    async def retrieve(
        self,
        settings: Settings,
        user: CurrentUser,
        episode: DecisionEpisode,
    ) -> RetrievedDecisionContext:
        profile = await self._confirmed_profile(settings, user)
        memories = await self._load_memories(settings, user)
        history = await self._load_history(settings, user, episode.id)
        now = datetime.now(timezone.utc)
        return RetrievedDecisionContext(
            profile=profile,
            memories=self.filter_memories(episode, memories, now),
            historical_episodes=self.filter_history(episode, history, now),
            retrieved_at=now,
        )

    async def _confirmed_profile(
        self,
        settings: Settings,
        user: CurrentUser,
    ) -> ConfirmedProfile | None:
        v2_profile = await self._v2_confirmed_profile(settings, user)
        if v2_profile is not None:
            return v2_profile
        try:
            profile = await get_profile(settings, user)
        except HTTPException as exc:
            if exc.status_code == 404:
                return None
            raise
        return profile if profile.status == "confirmed" else None

    async def _v2_confirmed_profile(
        self,
        settings: Settings,
        user: CurrentUser,
    ) -> PersonalDecisionProfile | None:
        async with httpx.AsyncClient(timeout=10) as client:
            aggregate_response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/personal_decision_profiles",
                params={
                    "user_id": f"eq.{user.id}", "status": "eq.confirmed",
                    "select": "*", "limit": "1",
                },
                headers=self._headers(settings, user),
            )
        if aggregate_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to retrieve confirmed profile")
        aggregates = aggregate_response.json()
        if not aggregates:
            return None
        aggregate = aggregates[0]
        version_id = aggregate.get("confirmed_version_id")
        if not version_id:
            return None
        async with httpx.AsyncClient(timeout=10) as client:
            version_response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_profile_versions",
                params={
                    "id": f"eq.{version_id}", "user_id": f"eq.{user.id}",
                    "status": "eq.confirmed", "select": "*", "limit": "1",
                },
                headers=self._headers(settings, user),
            )
        if version_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to retrieve profile version")
        versions = version_response.json()
        if not versions:
            return None
        version = versions[0]
        return PersonalDecisionProfile(
            id=aggregate["id"], user_id=aggregate["user_id"],
            schema_version=aggregate.get("schema_version", "2.0"), status="confirmed",
            version=version["version"], stable_profile=version.get("stable_profile", {}),
            dynamic_context=version.get("dynamic_context", {}),
            decision_style=version.get("decision_style", []),
            confirmed_at=version.get("confirmed_at"),
            last_reviewed_at=version.get("last_reviewed_at") or aggregate.get("last_reviewed_at"),
            created_at=aggregate["created_at"], updated_at=aggregate["updated_at"],
        )

    async def _load_memories(
        self,
        settings: Settings,
        user: CurrentUser,
    ) -> list[DecisionMemory]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_memories",
                params={
                    "user_id": f"eq.{user.id}",
                    "status": "eq.active",
                    "select": "*",
                    "order": "updated_at.desc",
                    "limit": "50",
                },
                headers=self._headers(settings, user),
            )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to retrieve decision memories")
        return [DecisionMemory.model_validate(row) for row in response.json()]

    async def _load_history(
        self,
        settings: Settings,
        user: CurrentUser,
        current_episode_id: UUID,
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/decision_episodes",
                params={
                    "id": f"neq.{current_episode_id}",
                    "user_id": f"eq.{user.id}",
                    "status": "in.(reflected,archived)",
                    "final_decision": "not.is.null",
                    "select": "id,domain,decision_question,final_decision,decision_rationale,closed_at,updated_at",
                    "order": "updated_at.desc",
                    "limit": "50",
                },
                headers=self._headers(settings, user),
            )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to retrieve decision history")
        return response.json()

    @classmethod
    def filter_memories(
        cls,
        episode: DecisionEpisode,
        memories: list[DecisionMemory],
        now: datetime,
    ) -> list[RelevantMemory]:
        query_tokens = cls._tokens(cls._episode_text(episode))
        selected: list[RelevantMemory] = []
        for memory in memories:
            if memory.status.value != "active" or memory.confidence < MIN_MEMORY_CONFIDENCE:
                continue
            if memory.effective_from and cls._utc(memory.effective_from) > now:
                continue
            if memory.effective_until and cls._utc(memory.effective_until) <= now:
                continue
            domain_match = cls._domain_match(episode.domain, memory.applicable_domains)
            overlap = cls._overlap(query_tokens, cls._tokens(memory.content))
            relevance = min(1.0, (0.55 if domain_match else 0) + 0.35 * overlap + 0.1 * memory.confidence)
            if not domain_match and overlap < 0.08:
                continue
            selected.append(RelevantMemory(memory=memory, relevance=round(relevance, 3)))
        return sorted(
            selected,
            key=lambda item: (item.relevance, item.memory.confidence, item.memory.updated_at),
            reverse=True,
        )[:MAX_MEMORIES]

    @classmethod
    def filter_history(
        cls,
        episode: DecisionEpisode,
        rows: list[dict[str, Any]],
        now: datetime,
    ) -> list[HistoricalEpisodeContext]:
        query_tokens = cls._tokens(cls._episode_text(episode))
        selected: list[HistoricalEpisodeContext] = []
        for row in rows:
            final_decision = row.get("final_decision")
            if not final_decision:
                continue
            domain_match = cls._domain_match(episode.domain, [row.get("domain")])
            candidate_text = " ".join(
                str(value or "")
                for value in [
                    row.get("decision_question"), final_decision, row.get("decision_rationale")
                ]
            )
            overlap = cls._overlap(query_tokens, cls._tokens(candidate_text))
            closed_at = cls._parse_datetime(row.get("closed_at") or row.get("updated_at"))
            age_days = max(0, (now - closed_at).days) if closed_at else 3650
            recency = max(0.0, 1 - age_days / 3650)
            relevance = min(1.0, (0.6 if domain_match else 0) + 0.3 * overlap + 0.1 * recency)
            if not domain_match and overlap < 0.12:
                continue
            selected.append(HistoricalEpisodeContext(
                id=UUID(str(row["id"])),
                domain=row.get("domain"),
                decision_question=row["decision_question"],
                final_decision=final_decision,
                decision_rationale=row.get("decision_rationale"),
                closed_at=closed_at,
                relevance=round(relevance, 3),
            ))
        return sorted(selected, key=lambda item: (item.relevance, item.closed_at or now), reverse=True)[
            :MAX_HISTORICAL_EPISODES
        ]

    @staticmethod
    def _headers(settings: Settings, user: CurrentUser) -> dict[str, str]:
        return {
            "apikey": settings.supabase_anon_key or "",
            "Authorization": f"Bearer {user.access_token}",
        }

    @staticmethod
    def _episode_text(episode: DecisionEpisode) -> str:
        values: list[object] = [
            episode.title, episode.decision_question, episode.domain, episode.background,
            episode.goal, *episode.values, *episode.facts, *episode.constraints, *episode.options,
        ]
        return " ".join(str(value) for value in values if value)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        lowered = text.lower()
        words = set(re.findall(r"[a-z0-9]+", lowered))
        chinese_runs = re.findall(r"[\u4e00-\u9fff]+", lowered)
        bigrams = {
            run[index:index + 2]
            for run in chinese_runs
            for index in range(max(0, len(run) - 1))
        }
        return (words | bigrams) - STOP_TOKENS

    @staticmethod
    def _overlap(query: set[str], candidate: set[str]) -> float:
        if not query or not candidate:
            return 0.0
        return len(query & candidate) / max(1, min(len(query), len(candidate)))

    @staticmethod
    def _domain_match(domain: str | None, candidate_domains: list[str | None]) -> bool:
        if not domain:
            return False
        normalized = domain.strip().lower()
        return any(value and value.strip().lower() == normalized for value in candidate_domains)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @classmethod
    def _parse_datetime(cls, value: object) -> datetime | None:
        if isinstance(value, datetime):
            return cls._utc(value)
        if isinstance(value, str):
            return cls._utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
        return None
ConfirmedProfile = ProfileResponse | PersonalDecisionProfile
