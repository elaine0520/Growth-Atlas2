import { useCallback, useEffect, useState } from "react";
import { Session } from "@supabase/supabase-js";
import AuthScreen from "./features/auth/AuthScreen";
import { supabase, supabaseConfigurationError } from "./lib/supabase";
import ProfileSetup from "./features/profile-setup/ProfileSetup";
import Reflection from "./features/reflection/Reflection";
import GrowthReport from "./features/growth-report/GrowthReport";
import DecisionTimeline from "./features/decision-timeline/DecisionTimeline";
import DecisionCreation from "./features/decision-episode/DecisionCreation";
import DecisionEpisodeDetail from "./features/decision-episode/DecisionEpisodeDetail";
import DecisionReview from "./features/decision-episode/DecisionReview";
import DecisionExecution from "./features/decision-episode/DecisionExecution";
import MemoryPage from "./features/memory/MemoryPage";
import { AppRoute, parseAppRoute, restoreLegacyRoute, routeToHash } from "./routing";

function initialRoute(): AppRoute {
  return parseAppRoute(window.location.hash) ?? restoreLegacyRoute();
}

function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [route, setRoute] = useState<AppRoute>(initialRoute);

  const navigate = useCallback((next: AppRoute, replace = false) => {
    const hash = routeToHash(next);
    if (replace) window.history.replaceState(null, "", hash);
    else window.history.pushState(null, "", hash);
    setRoute(next);
  }, []);

  useEffect(() => {
    if (!parseAppRoute(window.location.hash)) navigate(route, true);
    const restoreFromUrl = () => setRoute(parseAppRoute(window.location.hash) ?? { page: "profile" });
    window.addEventListener("popstate", restoreFromUrl);
    window.addEventListener("hashchange", restoreFromUrl);
    return () => {
      window.removeEventListener("popstate", restoreFromUrl);
      window.removeEventListener("hashchange", restoreFromUrl);
    };
  }, [navigate, route]);

  useEffect(() => {
    if (supabaseConfigurationError) return;
    void supabase.auth.getSession()
      .then(({ data, error }) => setSession(error ? null : data.session))
      .catch(() => setSession(null));
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => setSession(nextSession));
    return () => data.subscription.unsubscribe();
  }, []);

  if (supabaseConfigurationError) {
    return <main className="loading-screen" role="alert"><section>
      <h1>Growth Atlas 暂时无法启动</h1>
      <p>{supabaseConfigurationError}</p>
    </section></main>;
  }
  if (session === undefined) return <main className="loading-screen">正在连接 Growth Atlas…</main>;
  if (!session) return <AuthScreen onAuthenticated={() => navigate({ page: "profile" }, true)} />;

  switch (route.page) {
    case "profile":
      return <ProfileSetup session={session}
        onStartDecision={() => navigate({ page: "decision-create" })}
        onOpenMemory={() => navigate({ page: "memory" })}
        onOpenGrowthMap={() => navigate({ page: "timeline" })} />;
    case "decision-create":
      return <DecisionCreation session={session} episodeId={route.episodeId ?? ""}
        onBack={() => navigate({ page: "profile" })}
        onCreated={(episodeId) => navigate({ page: "decision-create", episodeId }, true)}
        onReady={(episodeId) => navigate({ page: "episode-detail", episodeId }, true)} />;
    case "episode-detail":
      return <DecisionEpisodeDetail session={session} episodeId={route.episodeId}
        onEdit={() => navigate({ page: "decision-create", episodeId: route.episodeId })}
        onReview={() => navigate({ page: "decision-review", episodeId: route.episodeId })}
        onExecute={() => navigate({ page: "decision-execution", episodeId: route.episodeId })}
        onNew={() => navigate({ page: "decision-create" })} />;
    case "decision-review":
      return <DecisionReview session={session} episodeId={route.episodeId}
        onBack={() => navigate({ page: "episode-detail", episodeId: route.episodeId })}
        onConfirmed={() => navigate({ page: "episode-detail", episodeId: route.episodeId }, true)} />;
    case "decision-execution":
      return <DecisionExecution session={session} episodeId={route.episodeId}
        onBack={() => navigate({ page: "episode-detail", episodeId: route.episodeId })}
        onMemory={(feedbackId) => navigate({
          page: "memory",
          feedbackId,
          returnEpisodeId: route.episodeId,
        })} />;
    case "memory":
      return <MemoryPage session={session} feedbackId={route.feedbackId}
        onBack={() => route.returnEpisodeId
          ? navigate({ page: "decision-execution", episodeId: route.returnEpisodeId })
          : navigate({ page: "profile" })} />;
    case "timeline":
      return <DecisionTimeline session={session}
        onBack={() => navigate({ page: "profile" })}
        onOpenEpisode={(episodeId) => navigate({ page: "episode-detail", episodeId })} />;
    case "report":
      return <GrowthReport session={session} reportId={route.reportId}
        onBack={() => navigate({ page: "timeline" })}
        onNewReflection={() => navigate({ page: "reflection" })} />;
    case "reflection":
      return <Reflection session={session}
        onBack={() => navigate({ page: "profile" })}
        onComplete={(reportId) => navigate({ page: "report", reportId }, true)} />;
  }
}

export default App;
