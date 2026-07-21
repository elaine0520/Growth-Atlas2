"""AI generation of reviewable V2 Decision Report Draft content."""

import json

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.models.decision_episode_v2 import DecisionEpisode
from app.models.decision_report_draft_v2 import DecisionOptionV2, ReportSectionV2
from app.services.decision_context_retrieval import RetrievedDecisionContext
from app.services.decision_draft_context_builder import (
    DecisionDraftContext,
    DecisionDraftContextBuilder,
)


PROMPT_VERSION = "decision-draft-v2"
SYSTEM_PROMPT = """你是 Growth Atlas 的决策分析助手。你的输出只能是一份供用户审阅的草稿，
不是用户的最终决定。使用中文，并完整分析 Goal、Values、Facts、Uncertainty、Constraints、
Options、Risks、Opportunity Cost、Reversibility 和 Recommendation。

规则：
- 区分已知事实、用户判断、假设、预测和未知信息，不虚构事实。
- 每个选项分别记录收益、成本、风险、机会成本、长期影响和可逆性。
- 推荐必须说明依据、关键条件和什么新信息会改变推荐。
- 不使用“你必须”或“唯一正确”，不把推荐写成用户已经确认的决定。
- 只返回符合给定 JSON Schema 的 JSON，不使用 Markdown 代码块。"""


class DecisionDraftContent(BaseModel):
    """The ten required analysis dimensions, mapped to the V2 persistence model."""

    model_config = ConfigDict(extra="forbid")

    goal_clarification: ReportSectionV2
    values_analysis: ReportSectionV2
    facts_analysis: ReportSectionV2
    assumptions: list[str] = Field(default_factory=list)
    uncertainty: list[str]
    constraints_analysis: ReportSectionV2
    options: list[DecisionOptionV2] = Field(min_length=1)
    recommendation: ReportSectionV2
    recommendation_conditions: list[str] = Field(default_factory=list)
    change_conditions: list[str] = Field(default_factory=list)


class AIDecisionDraftService:
    def __init__(
        self,
        settings: Settings,
        context_builder: DecisionDraftContextBuilder | None = None,
    ) -> None:
        if not settings.kimi_api_key:
            raise ValueError("KIMI_API_KEY is not configured")
        self._client = AsyncOpenAI(
            api_key=settings.kimi_api_key,
            base_url=settings.kimi_base_url,
            timeout=settings.ai_timeout_seconds,
            max_retries=2,
        )
        self._model = settings.kimi_model
        self._output_attempts = settings.ai_output_attempts
        self._context_builder = context_builder or DecisionDraftContextBuilder()

    @property
    def model_name(self) -> str:
        return self._model

    def build_context(
        self,
        episode: DecisionEpisode,
        retrieved: RetrievedDecisionContext | None,
    ) -> DecisionDraftContext:
        schema = json.dumps(DecisionDraftContent.model_json_schema(), ensure_ascii=False)
        return self._context_builder.build(
            episode,
            f"{SYSTEM_PROMPT}\n\nJSON Schema:\n{schema}",
            retrieved,
        )

    async def generate(
        self,
        episode: DecisionEpisode,
        retrieved: RetrievedDecisionContext | None,
    ) -> tuple[DecisionDraftContent, DecisionDraftContext]:
        context = self.build_context(episode, retrieved)
        last_error: ValueError | None = None
        for _attempt in range(self._output_attempts):
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=context.messages,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                last_error = ValueError("empty response")
                continue
            try:
                return DecisionDraftContent.model_validate_json(content), context
            except ValueError as exc:
                last_error = exc
        raise RuntimeError("AI provider returned an invalid decision draft") from last_error
