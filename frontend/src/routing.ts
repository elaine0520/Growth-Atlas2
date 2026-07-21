export type AppRoute =
  | { page: "profile" }
  | { page: "decision-create"; episodeId?: string }
  | { page: "episode-detail"; episodeId: string }
  | { page: "decision-review"; episodeId: string }
  | { page: "decision-execution"; episodeId: string }
  | { page: "memory"; feedbackId?: string; returnEpisodeId?: string }
  | { page: "timeline" }
  | { page: "reflection" }
  | { page: "report"; reportId: string };

function decoded(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return "";
  }
}

export function parseAppRoute(hash: string): AppRoute | null {
  const raw = hash.replace(/^#/, "") || "/profile";
  const [pathname, query = ""] = raw.split("?", 2);
  const parts = pathname.split("/").filter(Boolean).map(decoded);
  const params = new URLSearchParams(query);

  if (parts.length === 1 && parts[0] === "profile") return { page: "profile" };
  if (parts.length === 1 && parts[0] === "growth-map") return { page: "timeline" };
  if (parts.length === 1 && parts[0] === "memory") {
    return {
      page: "memory",
      feedbackId: params.get("feedback") || undefined,
      returnEpisodeId: params.get("episode") || undefined,
    };
  }
  if (parts[0] === "decisions" && parts[1] === "new" && parts.length === 2) {
    return { page: "decision-create" };
  }
  if (parts[0] === "decisions" && parts[1]) {
    const episodeId = parts[1];
    if (parts.length === 2) return { page: "episode-detail", episodeId };
    if (parts[2] === "edit") return { page: "decision-create", episodeId };
    if (parts[2] === "review") return { page: "decision-review", episodeId };
    if (parts[2] === "execution") return { page: "decision-execution", episodeId };
  }
  if (parts[0] === "legacy" && parts[1] === "reflection") return { page: "reflection" };
  if (parts[0] === "legacy" && parts[1] === "reports" && parts[2]) {
    return { page: "report", reportId: parts[2] };
  }
  return null;
}

export function routeToHash(route: AppRoute): string {
  switch (route.page) {
    case "profile": return "#/profile";
    case "timeline": return "#/growth-map";
    case "reflection": return "#/legacy/reflection";
    case "report": return `#/legacy/reports/${encodeURIComponent(route.reportId)}`;
    case "decision-create": return route.episodeId
      ? `#/decisions/${encodeURIComponent(route.episodeId)}/edit`
      : "#/decisions/new";
    case "episode-detail": return `#/decisions/${encodeURIComponent(route.episodeId)}`;
    case "decision-review": return `#/decisions/${encodeURIComponent(route.episodeId)}/review`;
    case "decision-execution": return `#/decisions/${encodeURIComponent(route.episodeId)}/execution`;
    case "memory": {
      const params = new URLSearchParams();
      if (route.feedbackId) params.set("feedback", route.feedbackId);
      if (route.returnEpisodeId) params.set("episode", route.returnEpisodeId);
      const query = params.toString();
      return `#/memory${query ? `?${query}` : ""}`;
    }
  }
}

export function restoreLegacyRoute(): AppRoute {
  const episodeId = sessionStorage.getItem("growth-atlas-episode-id") || undefined;
  const view = sessionStorage.getItem("growth-atlas-episode-view");
  const reportId = sessionStorage.getItem("growth-atlas-report-id") || undefined;
  const feedbackId = sessionStorage.getItem("growth-atlas-memory-feedback-id") || undefined;

  if (view === "memory") return { page: "memory", feedbackId, returnEpisodeId: episodeId };
  if (view === "timeline") return { page: "timeline" };
  if (episodeId && view === "review") return { page: "decision-review", episodeId };
  if (episodeId && view === "execution") return { page: "decision-execution", episodeId };
  if (episodeId && view === "detail") return { page: "episode-detail", episodeId };
  if (episodeId) return { page: "decision-create", episodeId };
  if (reportId) return { page: "report", reportId };
  return { page: "profile" };
}
