import type { Session } from "@supabase/supabase-js";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export type DecisionEpisodeStatus =
  | "capturing" | "ready_for_analysis" | "analyzing" | "draft_ready"
  | "awaiting_user_decision" | "committed" | "acting" | "awaiting_feedback"
  | "reflected" | "archived" | "analysis_failed" | "cancelled" | "abandoned";

export type DecisionEpisode = {
  id: string;
  user_id: string;
  schema_version: "2.0";
  title: string;
  decision_question: string;
  domain: string | null;
  importance: number | null;
  background: string | null;
  goal: string | null;
  values: string[];
  facts: string[];
  assumptions: string[];
  unknowns: string[];
  constraints: string[];
  options: string[];
  final_decision: string | null;
  decision_rationale: string | null;
  confirmed_from_draft_id: string | null;
  status: DecisionEpisodeStatus;
  created_at: string;
  updated_at: string;
};

export type ReportSection = { summary: string; points: string[] };
export type DecisionOption = {
  name: string;
  benefits: string[];
  costs: string[];
  risks: string[];
  opportunity_costs: string[];
  long_term_impacts: string[];
  reversibility: string | null;
};
export type DecisionReportDraft = {
  id: string;
  decision_episode_id: string;
  version: number;
  status: "generating" | "ready" | "accepted" | "rejected" | "superseded" | "invalid" | "generation_failed";
  goal_clarification: ReportSection | null;
  values_analysis: ReportSection | null;
  facts_analysis: ReportSection | null;
  assumptions: string[];
  uncertainty: string[];
  constraints_analysis: ReportSection | null;
  options: DecisionOption[];
  recommendation: ReportSection | null;
  recommendation_conditions: string[];
  change_conditions: string[];
};

export type DecisionEpisodeCreate = {
  title: string;
  decision_question: string;
  domain?: string | null;
  importance?: number | null;
};

export type DecisionEpisodeUpdate = Partial<Pick<
  DecisionEpisode,
  "title" | "decision_question" | "domain" | "importance" | "background" |
  "goal" | "values" | "facts" | "assumptions" | "unknowns" | "constraints" | "options"
>>;

async function request<T = DecisionEpisode>(
  session: Session,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${apiBase}/decision-episodes${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `决策事件请求失败（${response.status}）`);
  }
  return response.json() as Promise<T>;
}

export const decisionEpisodeApi = {
  create: (session: Session, payload: DecisionEpisodeCreate) =>
    request(session, "", { method: "POST", body: JSON.stringify(payload) }),
  load: (session: Session, id: string) => request(session, `/${id}`),
  update: (session: Session, id: string, payload: DecisionEpisodeUpdate) =>
    request(session, `/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  ready: (session: Session, id: string) =>
    request(session, `/${id}/ready`, { method: "POST" }),
  generateDraft: (session: Session, id: string) =>
    request<DecisionReportDraft>(session, `/${id}/drafts/generate`, { method: "POST" }),
  latestReadyDraft: (session: Session, id: string) =>
    request<DecisionReportDraft>(session, `/${id}/drafts/latest/ready`),
  confirm: (
    session: Session,
    id: string,
    payload: { draft_id: string; final_decision: string; decision_rationale?: string | null },
  ) => request(session, `/${id}/confirm`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
};
