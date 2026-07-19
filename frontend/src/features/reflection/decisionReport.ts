import type { Session } from "@supabase/supabase-js";

export type AnalysisSection = { summary: string; points: string[] };
export type DecisionReport = {
  goal_clarification: AnalysisSection;
  facts_analysis: AnalysisSection;
  constraints_analysis: AnalysisSection;
  options_comparison: AnalysisSection;
  decision_recommendation: AnalysisSection;
  action_plan: AnalysisSection;
};
export type SavedDecisionReport = {
  id: string;
  decision_case_id: string;
  question: string;
  report: DecisionReport;
  action_plan: AnalysisSection;
  model_name: string | null;
  prompt_version: string | null;
  created_at: string;
};
export type DecisionTimelineItem = {
  id: string;
  decision_case_id: string;
  question: string;
  decision_summary: string;
  created_at: string;
};

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export async function readDecisionReport(
  session: Session,
  reportId: string,
): Promise<SavedDecisionReport> {
  const response = await fetch(`${API_BASE_URL}/reflection/reports/${reportId}`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? "无法读取决策报告，请稍后重试。");
  }
  return response.json() as Promise<SavedDecisionReport>;
}

export async function readDecisionTimeline(session: Session): Promise<DecisionTimelineItem[]> {
  const response = await fetch(`${API_BASE_URL}/reflection/timeline`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  if (!response.ok) throw new Error("无法读取决策历史，请稍后重试。");
  return response.json() as Promise<DecisionTimelineItem[]>;
}
