import type { Session } from "@supabase/supabase-js";
import type { ProfileRecord, ProfileUpdate } from "./types";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request(
  session: Session,
  path = "",
  init?: RequestInit,
): Promise<ProfileRecord> {
  const response = await fetch(`${apiBase}/profile${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `档案请求失败（${response.status}）`);
  }
  return response.json() as Promise<ProfileRecord>;
}

export const profileApi = {
  load: (session: Session) => request(session),
  save: (session: Session, update: ProfileUpdate) =>
    request(session, "", { method: "PUT", body: JSON.stringify(update) }),
  confirm: (session: Session) => request(session, "/confirm", { method: "POST" }),
};
