import { useEffect, useState } from "react";
import { Session } from "@supabase/supabase-js";
import AuthScreen from "./features/auth/AuthScreen";
import { supabase } from "./lib/supabase";
import ProfileSetup from "./features/profile-setup/ProfileSetup";
import Reflection from "./features/reflection/Reflection";
import GrowthReport from "./features/growth-report/GrowthReport";
import DecisionTimeline from "./features/decision-timeline/DecisionTimeline";

function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const rememberedReportId = sessionStorage.getItem("growth-atlas-report-id") ?? "";
  const [page, setPage] = useState<"profile" | "reflection" | "report" | "timeline">(rememberedReportId ? "report" : "profile");
  const [reportId, setReportId] = useState(rememberedReportId);

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => setSession(nextSession));
    return () => data.subscription.unsubscribe();
  }, []);

  if (session === undefined) return <main className="loading-screen">正在连接 Growth Atlas…</main>;
  if (!session) return <AuthScreen />;

  if (page === "profile") {
    return <ProfileSetup session={session} onStartReflection={() => setPage("reflection")} />;
  }

  if (page === "report") {
    return (
      <GrowthReport
        session={session}
        reportId={reportId}
        onBack={() => setPage("timeline")}
        onNewReflection={() => {
          sessionStorage.removeItem("growth-atlas-report-id");
          setReportId("");
          setPage("reflection");
        }}
      />
    );
  }

  if (page === "timeline") return <DecisionTimeline session={session} onBack={() => setPage("reflection")} onOpenReport={(id) => { setReportId(id); setPage("report"); }} />;

  return (
    <Reflection
      session={session}
      onBack={() => setPage("profile")}
      onComplete={(nextReportId) => {
        sessionStorage.setItem("growth-atlas-report-id", nextReportId);
        setReportId(nextReportId);
        setPage("report");
      }}
    />
  );
}
export default App;
