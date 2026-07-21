import type { Session } from "@supabase/supabase-js";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export type EvidenceReference = {
  source_type: "user_input" | "user_confirmed" | "decision_episode" | "feedback" | "ai_observation" | "legacy_import";
  source_id: string | null;
  note: string | null;
};
export type MemoryType = "decision_experience" | "confirmed_lesson" | "effective_strategy" | "known_constraint" | "decision_pattern" | "profile_change";
export type MemoryCandidate = {
  id: string;
  decision_episode_id: string;
  feedback_id: string | null;
  candidate_type: MemoryType;
  proposed_content: string;
  rationale: string;
  evidence: EvidenceReference[];
  applicable_domains: string[];
  confidence: number;
  status: "suggested" | "edited" | "confirmed" | "rejected" | "expired";
  created_at: string;
};
export type DecisionMemory = {
  id: string;
  source_candidate_id: string;
  memory_type: MemoryType;
  content: string;
  applicable_domains: string[];
  evidence: EvidenceReference[];
  confidence: number;
  status: "active" | "needs_review" | "superseded" | "disabled" | "archived" | "deleted";
  confirmed_at: string;
  updated_at: string;
};

async function request<T>(session: Session, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}/memory${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Memory 请求失败（${response.status}）`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const memoryApi = {
  list: (session: Session) => request<DecisionMemory[]>(session, ""),
  listCandidates: (session: Session) => request<MemoryCandidate[]>(session, "/candidates"),
  createCandidate: (session: Session, payload: {
    feedback_id: string;
    candidate_type: MemoryType;
    proposed_content: string;
    rationale: string;
    applicable_domains: string[];
  }) => request<MemoryCandidate>(session, "/candidates", { method: "POST", body: JSON.stringify(payload) }),
  confirmCandidate: (session: Session, id: string, content: string, applicableDomains: string[]) =>
    request<DecisionMemory>(session, `/candidates/${id}/confirm`, {
      method: "POST",
      body: JSON.stringify({ content, applicable_domains: applicableDomains, user_confirmed: true }),
    }),
  rejectCandidate: (session: Session, id: string) =>
    request<MemoryCandidate>(session, `/candidates/${id}/reject`, {
      method: "POST", body: JSON.stringify({}),
    }),
  setStatus: (session: Session, id: string, target: "active" | "disabled") =>
    request<DecisionMemory>(session, `/${id}`, {
      method: "PATCH", body: JSON.stringify({ target_status: target }),
    }),
  delete: (session: Session, id: string) => request<void>(session, `/${id}`, { method: "DELETE" }),
};
