"""Build a bounded, traceable AI context from retrieved decision evidence."""

from dataclasses import dataclass
from datetime import datetime

from app.models.decision_episode_v2 import DecisionEpisode
from app.models.decision_profile_v2 import PersonalDecisionProfile, ProfileItem
from app.schemas.profile import ProfileResponse
from app.services.decision_context_retrieval import RetrievedDecisionContext


CONTEXT_VERSION = "decision-context-builder-v2"
MAX_CONTEXT_CHARS = 16_000


@dataclass(frozen=True)
class DecisionDraftContext:
    system_prompt: str
    user_prompt: str
    snapshot: dict[str, object]
    version: str = CONTEXT_VERSION

    @property
    def messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]


class DecisionDraftContextBuilder:
    """Format only context selected by the V2 retrieval policy."""

    def build(
        self,
        episode: DecisionEpisode,
        system_prompt: str,
        retrieved: RetrievedDecisionContext | None = None,
    ) -> DecisionDraftContext:
        context = retrieved or RetrievedDecisionContext()
        profile_items = self._profile_items(context.profile, context.retrieved_at)
        memory_context = self._memory_context(context)
        history_context = self._history_context(context)
        user_prompt = (
            "请为以下正式决策事件生成一份可供用户审阅的分析草稿。\n\n"
            f"<decision_episode>\n{self._episode_context(episode)}\n</decision_episode>\n\n"
            f"<confirmed_profile>\n{self._lines_or_empty(profile_items)}\n</confirmed_profile>\n\n"
            f"<relevant_decision_memories>\n{memory_context}\n</relevant_decision_memories>\n\n"
            f"<relevant_historical_episodes>\n{history_context}\n</relevant_historical_episodes>\n\n"
            "只使用上述信息。当前决策中的用户说明优先于旧资料。历史经验只作为带来源的参考，"
            "不得直接决定当前方案；如历史信息可能失效或冲突，必须标记为待验证。"
            "明确区分事实、假设和未知信息，不得替用户作出最终决定。"
        )[:MAX_CONTEXT_CHARS]
        snapshot: dict[str, object] = {
            "profile_id": str(context.profile.id) if context.profile else None,
            "profile_version": context.profile.version if context.profile else None,
            "selected_profile_items": profile_items,
            "selected_memory_ids": [str(item.memory.id) for item in context.memories],
            "selected_historical_episode_ids": [
                str(item.id) for item in context.historical_episodes
            ],
            "memory_relevance": {
                str(item.memory.id): item.relevance for item in context.memories
            },
            "historical_episode_relevance": {
                str(item.id): item.relevance for item in context.historical_episodes
            },
            "current_user_input": episode.decision_question,
            "context_builder_version": CONTEXT_VERSION,
            "retrieval_version": context.version,
            "generated_at": context.retrieved_at.isoformat(),
        }
        return DecisionDraftContext(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            snapshot=snapshot,
        )

    @staticmethod
    def _episode_context(episode: DecisionEpisode) -> str:
        fields = {
            "标题": episode.title,
            "决策问题": episode.decision_question,
            "背景": episode.background,
            "目标": episode.goal,
            "价值": episode.values,
            "事实": episode.facts,
            "用户假设": episode.assumptions,
            "未知信息": episode.unknowns,
            "约束": episode.constraints,
            "已有选项": episode.options,
        }
        return "\n".join(f"- {key}: {value}" for key, value in fields.items() if value)

    @staticmethod
    def _profile_items(
        profile: ProfileResponse | PersonalDecisionProfile | None,
        now: datetime,
    ) -> list[str]:
        if profile is None or profile.status != "confirmed":
            return []
        if isinstance(profile, PersonalDecisionProfile):
            stable = profile.stable_profile
            dynamic = profile.dynamic_context
            items: list[tuple[str, ProfileItem]] = []
            for label, values in [
                ("长期目标", stable.long_term_goals),
                ("核心价值", stable.core_values),
                ("长期方向", stable.long_term_directions),
                ("重要原则", stable.important_principles),
                ("当前项目", dynamic.current_projects),
                ("当前压力", dynamic.current_pressures),
                ("当前资源", dynamic.current_resources),
                ("当前约束", dynamic.current_constraints),
            ]:
                items.extend((label, item) for item in values)
            if dynamic.current_stage:
                items.append(("当前阶段", dynamic.current_stage))
            if dynamic.current_environment:
                items.append(("当前环境", dynamic.current_environment))
            selected = [
                f"{label}: {item.content}"
                for label, item in items
                if item.confirmed_at
                and (item.effective_from is None or item.effective_from <= now)
                and (item.effective_until is None or item.effective_until > now)
            ]
            selected.extend(
                f"决策观察({item.domain}, 置信度 {item.confidence:.2f}): {item.observation}"
                for item in profile.decision_style
                if item.user_confirmed and item.confidence >= 0.5
                and (item.valid_until is None or item.valid_until > now)
            )
            return selected
        fields: list[tuple[str, object]] = [
            ("人生阶段", profile.user_info.life_stage),
            ("当前情境", profile.current_context),
            ("短期目标", profile.short_term_goals),
            ("长期目标", profile.long_term_goals),
            ("价值排序", profile.values),
            ("主要压力", profile.pressure_sources),
        ]
        return [f"{label}: {value}" for label, value in fields if value]

    @staticmethod
    def _memory_context(context: RetrievedDecisionContext) -> str:
        if not context.memories:
            return "没有通过相关性、有效期和置信度筛选的长期记忆。"
        blocks = []
        for item in context.memories:
            memory = item.memory
            sources = ", ".join(
                f"{evidence.source_type.value}:{evidence.source_id}" for evidence in memory.evidence
            )
            blocks.append(
                f"- Memory {memory.id} | 类型={memory.memory_type.value} | "
                f"置信度={memory.confidence:.2f} | 相关性={item.relevance:.3f} | "
                f"内容={memory.content} | 来源={sources}"
            )
        return "\n".join(blocks)

    @staticmethod
    def _history_context(context: RetrievedDecisionContext) -> str:
        if not context.historical_episodes:
            return "没有通过相关性筛选的历史决策。"
        return "\n".join(
            f"- Episode {item.id} | 领域={item.domain or '未分类'} | "
            f"相关性={item.relevance:.3f} | 当时问题={item.decision_question} | "
            f"用户决定={item.final_decision} | 理由={item.decision_rationale or '未记录'}"
            for item in context.historical_episodes
        )

    @staticmethod
    def _lines_or_empty(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "没有已确认 Profile。"
