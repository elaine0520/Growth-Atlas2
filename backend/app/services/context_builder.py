"""Build the minimal, user-owned context sent to the AI provider."""

from dataclasses import dataclass

from app.schemas.profile import ProfileResponse


CONTEXT_VERSION = "profile-context-v1"
MAX_CONTEXT_CHARS = 6_000
MAX_ITEM_CHARS = 500


@dataclass(frozen=True)
class AIContext:
    """The complete provider input for one Reflection analysis."""

    system_prompt: str
    user_prompt: str
    profile_context: str
    version: str = CONTEXT_VERSION

    @property
    def messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]


class ContextBuilder:
    """Select and bound Profile fields; conversation history is not accepted."""

    def build(self, question: str, profile: ProfileResponse, system_prompt: str) -> AIContext:
        profile_context = self._build_profile_context(profile)
        user_prompt = (
            "请分析下面的当前决策问题。\n\n"
            "<current_user_profile>\n"
            f"{profile_context}\n"
            "</current_user_profile>\n\n"
            "<current_question>\n"
            f"{question.strip()}\n"
            "</current_question>\n\n"
            "必须把档案中的目标、价值排序、现实情境和压力用于方案比较与建议；"
            "至少在目标澄清、约束分析或决策建议中明确说明相关依据。"
            "若档案与当前问题冲突，以当前问题为准，并指出冲突。"
            "不要虚构档案未提供的信息。"
        )
        return AIContext(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            profile_context=profile_context,
        )

    def _build_profile_context(self, profile: ProfileResponse) -> str:
        info = profile.user_info
        sections = [
            self._line("档案状态", f"{profile.status}（版本 {profile.version}）"),
            self._line("称呼", info.nickname),
            self._line("年龄阶段", info.age_range),
            self._line("人生阶段", info.life_stage),
            self._line("背景", info.background),
            self._line("当前情境", profile.current_context),
            self._items("主要压力", profile.pressure_sources),
            self._items("短期目标", profile.short_term_goals),
            self._items("长期目标", profile.long_term_goals),
            self._items("重视的价值", profile.values),
            self._items("自我描述", profile.self_description),
        ]
        context = "\n".join(section for section in sections if section)
        if not context:
            context = "档案暂无有效内容"
        return context[:MAX_CONTEXT_CHARS]

    @staticmethod
    def _clean(value: str | None) -> str:
        if not value:
            return ""
        return " ".join(value.split())[:MAX_ITEM_CHARS]

    def _line(self, label: str, value: str | None) -> str:
        cleaned = self._clean(value)
        return f"- {label}：{cleaned}" if cleaned else ""

    def _items(self, label: str, values: list[str]) -> str:
        cleaned = [self._clean(value) for value in values]
        present = [value for value in cleaned if value]
        return f"- {label}：{'；'.join(present)}" if present else ""
