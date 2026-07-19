import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  readDecisionReport,
  type DecisionReport,
  type SavedDecisionReport,
} from "../reflection/decisionReport";

type Props = {
  session: Session;
  reportId: string;
  onBack: () => void;
  onNewReflection: () => void;
};

const SECTION_META: Array<[keyof DecisionReport, string, string]> = [
  ["goal_clarification", "目标澄清", "GOAL CLARIFICATION"],
  ["facts_analysis", "事实分析", "FACTS ANALYSIS"],
  ["constraints_analysis", "约束分析", "CONSTRAINTS"],
  ["options_comparison", "方案比较", "OPTIONS"],
  ["decision_recommendation", "决策建议", "DECISION"],
  ["action_plan", "行动计划", "ACTION PLAN"],
];

function GrowthReport({ session, reportId, onBack, onNewReflection }: Props) {
  const [saved, setSaved] = useState<SavedDecisionReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setSaved(null);
    setError("");
    void readDecisionReport(session, reportId)
      .then((result) => { if (active) setSaved(result); })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "无法读取决策报告。");
      });
    return () => { active = false; };
  }, [reportId, session]);

  if (error) return <main className="loading-screen"><div><p>{error}</p><button className="primary-button" type="button" onClick={onBack}>返回分析</button></div></main>;
  if (!saved) return <main className="loading-screen">正在读取已保存的决策报告…</main>;

  const createdAt = new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" })
    .format(new Date(saved.created_at));

  return (
    <main className="growth-report-page">
      <header className="report-nav">
        <div className="brand"><span className="brand-mark">GA</span><span>Growth Atlas</span></div>
        <button className="nav-back" type="button" onClick={onBack}>← 返回分析</button>
      </header>

      <section className="report-hero">
        <div className="report-hero-copy">
          <p className="eyebrow">DECISION REPORT · 已保存</p>
          <h1>你的决策报告</h1>
          <p>这份报告来自本次真实 AI 分析，包含目标、事实、约束、选项、建议和可执行的下一步。</p>
          <div className="report-meta"><span>{saved.model_name ?? "AI 分析"}</span><span>{createdAt}</span></div>
        </div>
        <blockquote><span>本次核心问题</span><p>“{saved.question}”</p></blockquote>
      </section>

      <section className="report-content" aria-label="决策报告正文">
        {SECTION_META.map(([key, title, label], index) => {
          const section = saved.report[key];
          return (
            <article className={`report-section ${key === "action_plan" ? "report-section--action" : ""}`} key={key}>
              <div className="report-section-index"><span>{String(index + 1).padStart(2, "0")}</span><i /></div>
              <div className="report-section-copy">
                <p className="section-label">{label}</p><h2>{title}</h2>
                <p>{section.summary}</p>
                <div className="report-tags">{section.points.map((point, pointIndex) => <span key={`${key}-${pointIndex}`}>{point}</span>)}</div>
              </div>
            </article>
          );
        })}
      </section>

      <footer className="report-footer"><p className="eyebrow">REFLECTION → INSIGHT → DECISION → ACTION</p><h2>清晰一点，然后行动一步。</h2><p>报告已经保存。你可以返回重新阅读，也可以开始处理新的困惑。</p><button className="primary-button" type="button" onClick={onNewReflection}>开始新的 Reflection <span>→</span></button></footer>
    </main>
  );
}

export default GrowthReport;
