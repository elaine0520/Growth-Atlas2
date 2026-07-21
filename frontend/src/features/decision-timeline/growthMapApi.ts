import type { Session } from "@supabase/supabase-js";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export type TimelineActionItem = {
  id: string; description: string; status: string; completed_at: string | null;
};
export type TimelineActionPlan = {
  id: string; objective: string; status: string; success_criteria: string | null;
  confirmed_at: string | null; actions: TimelineActionItem[];
};
export type TimelineFeedback = {
  id: string; actual_outcome: string | null; expected_vs_actual: string | null;
  lessons_learned: string[]; confirmed_at: string | null;
};
export type ConfirmedExperience = {
  id: string; source_candidate_id: string; source_episode_id: string;
  memory_type: string; content: string; status: string;
  applicable_domains: string[]; confirmed_at: string;
};
export type DecisionTimelineEntry = {
  id: string; title: string; decision_question: string; domain: string | null;
  status: string; final_decision: string | null; decision_rationale: string | null;
  created_at: string; committed_at: string | null; closed_at: string | null;
  action_plan: TimelineActionPlan | null; feedback: TimelineFeedback[];
  confirmed_experiences: ConfirmedExperience[];
};
export type GrowthMap = {
  timeline: DecisionTimelineEntry[];
  confirmed_experiences: ConfirmedExperience[];
  generated_at: string;
};

export async function readGrowthMap(session: Session): Promise<GrowthMap> {
  const response = await fetch(`${apiBase}/growth-map`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Growth Map 请求失败（${response.status}）`);
  }
  return response.json() as Promise<GrowthMap>;
}
