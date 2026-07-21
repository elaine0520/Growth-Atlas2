import type { Session } from "@supabase/supabase-js";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export type ActionItem = {
  id: string;
  description: string;
  sequence: number;
  status: "pending" | "in_progress" | "completed" | "skipped";
  completion_note: string | null;
  completed_at: string | null;
};

export type ActionPlan = {
  id: string;
  decision_episode_id: string;
  status: "draft" | "confirmed" | "in_progress" | "completed" | "abandoned" | "superseded";
  objective: string;
  actions: ActionItem[];
  success_criteria: string | null;
  major_obstacles: string[];
  confirmed_at: string | null;
};

export type Feedback = {
  id: string;
  decision_episode_id: string;
  action_plan_id: string | null;
  status: "draft" | "pending_confirmation" | "confirmed" | "corrected" | "archived";
  actual_actions: string[];
  actual_outcome: string | null;
  expected_vs_actual: string | null;
  lessons_learned: string[];
  confirmed_at: string | null;
};

async function request<T>(session: Session, path: string, init?: RequestInit): Promise<T> {
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
    throw new Error(body?.detail ?? `Action/Feedback 请求失败（${response.status}）`);
  }
  return response.json() as Promise<T>;
}

export const actionFeedbackApi = {
  loadPlan: (session: Session, episodeId: string) =>
    request<ActionPlan>(session, `/${episodeId}/action-plan`),
  createPlan: (
    session: Session,
    episodeId: string,
    payload: { objective: string; actions: string[]; success_criteria?: string | null; major_obstacles: string[] },
  ) => request<ActionPlan>(session, `/${episodeId}/action-plan`, {
    method: "POST", body: JSON.stringify(payload),
  }),
  completeAction: (
    session: Session,
    episodeId: string,
    planId: string,
    itemId: string,
    completed: boolean,
  ) => request<ActionItem>(session, `/${episodeId}/action-plan/${planId}/actions/${itemId}`, {
    method: "PATCH", body: JSON.stringify({ completed }),
  }),
  submitFeedback: (
    session: Session,
    episodeId: string,
    payload: {
      action_plan_id: string;
      actual_actions: string[];
      actual_outcome: string;
      expected_vs_actual: string;
      lessons_learned: string[];
    },
  ) => request<Feedback>(session, `/${episodeId}/feedback`, {
    method: "POST", body: JSON.stringify(payload),
  }),
  loadFeedback: (session: Session, episodeId: string) =>
    request<Feedback>(session, `/${episodeId}/feedback/latest`),
};
