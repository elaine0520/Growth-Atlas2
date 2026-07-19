export type ProfileStatus = "draft" | "pending_confirmation" | "confirmed" | "archived";

export type ProfileFormData = {
  nickname: string;
  ageRange: string;
  lifeStage: string;
  background: string;
  currentContext: string;
  pressureSources: string;
  shortTermGoals: string;
  longTermGoals: string;
  values: string[];
  selfDescription: string;
};

export type ProfileRecord = {
  id: string;
  user_info: {
    nickname: string | null;
    age_range: string | null;
    life_stage: string | null;
    background: string | null;
    locale: string;
    timezone: string;
  };
  current_context: string | null;
  pressure_sources: string[];
  short_term_goals: string[];
  long_term_goals: string[];
  values: string[];
  self_description: string[];
  status: ProfileStatus;
  version: number;
  confirmed_at: string | null;
  last_reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ProfileUpdate = Pick<
  ProfileRecord,
  | "user_info"
  | "current_context"
  | "pressure_sources"
  | "short_term_goals"
  | "long_term_goals"
  | "values"
  | "self_description"
>;

export const EMPTY_PROFILE_FORM: ProfileFormData = {
  nickname: "",
  ageRange: "",
  lifeStage: "",
  background: "",
  currentContext: "",
  pressureSources: "",
  shortTermGoals: "",
  longTermGoals: "",
  values: [],
  selfDescription: "",
};

const lines = (value: string) =>
  value.split("\n").map((item) => item.trim()).filter(Boolean);

export function recordToForm(profile: ProfileRecord): ProfileFormData {
  return {
    nickname: profile.user_info.nickname ?? "",
    ageRange: profile.user_info.age_range ?? "",
    lifeStage: profile.user_info.life_stage ?? "",
    background: profile.user_info.background ?? "",
    currentContext: profile.current_context ?? "",
    pressureSources: profile.pressure_sources.join("\n"),
    shortTermGoals: profile.short_term_goals.join("\n"),
    longTermGoals: profile.long_term_goals.join("\n"),
    values: profile.values,
    selfDescription: profile.self_description.join("\n"),
  };
}

export function formToUpdate(form: ProfileFormData): ProfileUpdate {
  return {
    user_info: {
      nickname: form.nickname.trim() || null,
      age_range: form.ageRange.trim() || null,
      life_stage: form.lifeStage || null,
      background: form.background.trim() || null,
      locale: "zh-CN",
      timezone: "Asia/Shanghai",
    },
    current_context: form.currentContext.trim() || null,
    pressure_sources: lines(form.pressureSources),
    short_term_goals: lines(form.shortTermGoals),
    long_term_goals: lines(form.longTermGoals),
    values: form.values,
    self_description: lines(form.selfDescription),
  };
}
