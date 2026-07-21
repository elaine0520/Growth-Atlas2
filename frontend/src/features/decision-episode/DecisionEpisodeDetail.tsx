import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { decisionEpisodeApi, type DecisionEpisode } from "./decisionEpisodeApi";

type Props = {
  session: Session;
  episodeId: string;
  onEdit: () => void;
  onNew: () => void;
  onReview: () => void;
  onExecute: () => void;
};

export default function DecisionEpisodeDetail({ session, episodeId, onEdit, onNew, onReview, onExecute }: Props) {
  const [episode, setEpisode] = useState<DecisionEpisode | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void decisionEpisodeApi.load(session, episodeId)
      .then((value) => { if (active) setEpisode(value); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "读取失败"); });
    return () => { active = false; };
  }, [episodeId, session]);

  async function generateDraft() {
    setGenerating(true);
    setError("");
    try {
      await decisionEpisodeApi.generateDraft(session, episodeId);
      onReview();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "AI 草稿生成失败");
    } finally {
      setGenerating(false);
    }
  }

  if (error && !episode) return <main className="loading-screen">{error}</main>;
  if (!episode) return <main className="loading-screen">正在读取 Decision Episode…</main>;
  const canReview = episode.status === "draft_ready" || episode.status === "awaiting_user_decision";
  const canGenerate = episode.status === "ready_for_analysis" || episode.status === "analysis_failed";
  const canExecute = ["committed", "acting", "awaiting_feedback", "reflected"].includes(episode.status);

  return <main className="episode-detail-page">
    <header className="report-nav"><div className="brand"><span className="brand-mark">GA</span><span>Growth Atlas</span></div>
      {episode.status === "capturing" && <button className="nav-back" onClick={onEdit}>编辑背景</button>}</header>
    <section className="episode-detail-hero"><p className="eyebrow">DECISION EPISODE · {episode.status}</p>
      <h1>{episode.title}</h1><blockquote>“{episode.decision_question}”</blockquote></section>
    <section className="episode-detail-grid"><Detail title="为什么现在要决定" value={episode.background} />
      <Detail title="好结果的标准" value={episode.goal} /><Detail title="不愿牺牲的价值" items={episode.values} />
      <Detail title="已确认的信息" items={episode.facts} /><Detail title="待验证的判断" items={episode.assumptions} />
      <Detail title="还需要查清的信息" items={episode.unknowns} /><Detail title="暂时无法改变的条件" items={episode.constraints} />
      <Detail title="可以选择的做法" items={episode.options} /><Detail title="领域" value={episode.domain} />
      <Detail title="重要程度" value={episode.importance?.toString()} /></section>

    {episode.status === "committed" && <section className="committed-decision">
      <p className="eyebrow">USER CONFIRMED DECISION</p><h2>{episode.final_decision}</h2>
      {episode.decision_rationale && <p>{episode.decision_rationale}</p>}
      <small>AI 草稿和你的最终选择已分别保存。</small>
    </section>}

    <footer className="report-footer">
      {error && <p className="form-error">{error}</p>}
      {canGenerate && <button className="primary-button" disabled={generating} onClick={() => void generateDraft()}>
        {generating ? "正在生成 AI 草稿…" : "生成 AI 决策草稿"}</button>}
      {canReview && <button className="primary-button" onClick={onReview}>审阅并确认决定</button>}
      {canExecute && <button className="primary-button" onClick={onExecute}>
        {episode.status === "committed" ? "创建行动计划" : episode.status === "reflected" ? "查看行动与反馈" : "继续行动与反馈"}
      </button>}
      <button className="secondary-button" onClick={onNew}>创建新的 Decision Episode</button>
    </footer>
  </main>;
}

function Detail({ title, value, items }: { title: string; value?: string | null; items?: string[] }) {
  return <article className="episode-detail-card"><p className="eyebrow">{title}</p>
    {items ? (items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>尚未填写</p>) : <p>{value || "尚未填写"}</p>}
  </article>;
}
