import { type FormEvent, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  API_BASE_URL,
  type DecisionReport,
  type SavedDecisionReport,
} from "./decisionReport";

type Props = { session: Session; onBack: () => void; onComplete: (reportId: string) => void };

const SECTION_META: Array<[keyof DecisionReport, string, string]> = [
  ["goal_clarification", "目标澄清", "明确真正需要决定的问题"],
  ["facts_analysis", "事实分析", "区分事实、判断与未知信息"],
  ["constraints_analysis", "约束分析", "看清时间、资源、能力与环境"],
  ["options_comparison", "方案比较", "比较收益、成本、风险与可逆性"],
  ["decision_recommendation", "决策建议", "给出有依据的优先方向"],
  ["action_plan", "行动计划", "用行动验证，并设置反馈节点"],
];

function Reflection({ session, onBack, onComplete }: Props) {
  const [question, setQuestion] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [report, setReport] = useState<DecisionReport | null>(null);
  const [reportId, setReportId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/reflection/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ question: trimmed }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null) as { detail?: string } | null;
        throw new Error(body?.detail ?? "分析请求失败，请稍后重试。");
      }
      const saved = await response.json() as SavedDecisionReport;
      setReport(saved.report);
      setReportId(saved.id);
      setSubmitted(trimmed);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法连接分析服务，请检查后端是否启动。");
    } finally { setLoading(false); }
  };

  if (submitted && report) return <main className="reflection-page">
    <Nav onBack={onBack} />
    <section className="analysis-hero"><div><p className="eyebrow">STRUCTURED DECISION</p><h1>把选择一层层看清</h1><p>基于 Goal → Facts → Constraints → Options → Decision → Action → Feedback 的 AI 决策分析。</p></div><div className="question-summary"><span>你的决策问题</span><p>“{submitted}”</p></div></section>
    <section className="analysis-list" aria-label="结构化决策报告">{SECTION_META.map(([key, title, subtitle], index) => { const section = report[key]; return <article className="analysis-card" key={key}><div className="analysis-index">{String(index + 1).padStart(2, "0")}</div><div className="analysis-copy"><span>{subtitle}</span><h2>{title}</h2><p>{section.summary}</p><ul>{section.points.map((point, pointIndex) => <li key={`${key}-${pointIndex}`}>{point}</li>)}</ul>{key === "action_plan" && <div className="action-callout">反馈节点 · 按计划复盘新事实与关键假设，再决定是否调整方向</div>}</div></article>; })}</section>
    <footer className="analysis-footer"><p>分析已安全保存，可在完整报告中重新读取。</p><div className="analysis-footer-actions"><button className="text-button" onClick={() => { setQuestion(""); setSubmitted(""); setReport(null); setReportId(""); }}>记录新的困惑</button><button className="primary-button" onClick={() => onComplete(reportId)}>查看完整决策报告 <span>→</span></button></div></footer>
  </main>;

  return <main className="reflection-entry"><Nav onBack={onBack} light /><section className="reflection-entry-content"><div className="reflection-intro"><p className="eyebrow">REFLECTION · 01</p><h1>记录你的困惑</h1><p>不必组织得很完美。写下此刻最想梳理的一件事，我们会从目标、事实、约束、方案、决策与行动逐层展开。</p></div><form className="reflection-form" onSubmit={submit}><label htmlFor="question">此刻，你最需要决定什么？</label><textarea id="question" rows={8} maxLength={800} value={question} onChange={event => setQuestion(event.target.value)} placeholder="例如：我收到了一个不错的实习机会，但又担心它会影响备考。我不知道应该抓住机会，还是专注于原来的计划……" autoFocus /><div className="reflection-form-meta"><span>一次只聚焦一个核心问题</span><span>{question.length} / 800</span></div>{error && <p className="analysis-error" role="alert">{error}</p>}<button className="primary-button analyze-button" disabled={!question.trim() || loading}>{loading ? "正在进行 AI 决策分析…" : "开始结构化分析"}<span>→</span></button><p className="mock-note">当前问题与个人档案摘要将发送至 AI 服务用于本次分析；不会发送完整对话历史</p></form></section></main>;
}

function Nav({ onBack, light = false }: { onBack: () => void; light?: boolean }) { return <header className={`reflection-nav ${light ? "reflection-nav--light" : ""}`}><div className="brand"><span className="brand-mark">GA</span><span>Growth Atlas</span></div><button className="nav-back" onClick={onBack}>← 返回个人档案</button></header>; }
export default Reflection;
