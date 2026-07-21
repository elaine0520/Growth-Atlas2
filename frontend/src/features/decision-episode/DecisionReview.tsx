import { FormEvent, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  decisionEpisodeApi,
  type DecisionEpisode,
  type DecisionReportDraft,
  type ReportSection,
} from "./decisionEpisodeApi";

type Props = {
  session: Session;
  episodeId: string;
  onBack: () => void;
  onConfirmed: (episode: DecisionEpisode) => void;
};

export default function DecisionReview({ session, episodeId, onBack, onConfirmed }: Props) {
  const [episode, setEpisode] = useState<DecisionEpisode | null>(null);
  const [draft, setDraft] = useState<DecisionReportDraft | null>(null);
  const [finalDecision, setFinalDecision] = useState("");
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void Promise.all([
      decisionEpisodeApi.load(session, episodeId),
      decisionEpisodeApi.latestReadyDraft(session, episodeId),
    ]).then(([loadedEpisode, loadedDraft]) => {
      if (!active) return;
      setEpisode(loadedEpisode);
      setDraft(loadedDraft);
      setFinalDecision(loadedEpisode.final_decision ?? loadedDraft.recommendation?.summary ?? "");
      setRationale(loadedEpisode.decision_rationale ?? "");
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : "无法加载决策草稿");
    });
    return () => { active = false; };
  }, [episodeId, session]);

  async function confirm(event: FormEvent) {
    event.preventDefault();
    if (!draft || !finalDecision.trim()) return;
    setBusy(true);
    setError("");
    try {
      const committed = await decisionEpisodeApi.confirm(session, episodeId, {
        draft_id: draft.id,
        final_decision: finalDecision.trim(),
        decision_rationale: rationale.trim() || null,
      });
      onConfirmed(committed);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "确认失败，请稍后重试");
    } finally {
      setBusy(false);
    }
  }

  if (error && !draft) return <main className="loading-screen">{error}</main>;
  if (!episode || !draft) return <main className="loading-screen">正在读取 AI Decision Draft…</main>;

  return <main className="decision-review-page">
    <header className="report-nav">
      <div className="brand"><span className="brand-mark">GA</span><span>Growth Atlas</span></div>
      <button className="nav-back" onClick={onBack}>返回事件详情</button>
    </header>

    <section className="review-hero">
      <p className="eyebrow">USER REVIEW · DRAFT V{draft.version}</p>
      <h1>{episode.title}</h1>
      <p>下面是 AI 建议草稿。它不是你的决定，你可以采用、修改或选择完全不同的方案。</p>
    </section>

    <section className="review-grid">
      <div className="ai-draft-column">
        <h2>AI 分析草稿</h2>
        <DraftSection title="目标" section={draft.goal_clarification} />
        <DraftSection title="价值" section={draft.values_analysis} />
        <DraftSection title="事实" section={draft.facts_analysis} />
        <ListSection title="不确定性" items={draft.uncertainty} />
        <DraftSection title="约束" section={draft.constraints_analysis} />
        <div className="review-card"><h3>选项比较</h3>{draft.options.map((option) =>
          <article className="review-option" key={option.name}>
            <h4>{option.name}</h4>
            <ListSection title="收益" items={option.benefits} compact />
            <ListSection title="风险" items={option.risks} compact />
            <ListSection title="机会成本" items={option.opportunity_costs} compact />
            <p><strong>可逆性：</strong>{option.reversibility || "未说明"}</p>
          </article>)}
        </div>
        <DraftSection title="AI 建议" section={draft.recommendation} accent />
      </div>

      <form className="user-decision-column" onSubmit={confirm}>
        <p className="eyebrow">YOUR DECISION</p>
        <h2>记录你的最终选择</h2>
        <p className="review-note">此处内容属于你。修改不会覆盖或改写左侧 AI 草稿。</p>
        <label>最终选择<textarea required maxLength={5000} value={finalDecision}
          onChange={(event) => setFinalDecision(event.target.value)} /></label>
        <label>你的理由<textarea maxLength={5000} value={rationale}
          onChange={(event) => setRationale(event.target.value)} /></label>
        {error && <p className="form-error">{error}</p>}
        <button className="primary-button" disabled={busy || !finalDecision.trim()}>
          {busy ? "正在确认…" : "确认这是我的决定"}
        </button>
        <p className="confirmation-boundary">确认后，Decision Episode 将进入 committed 状态。</p>
      </form>
    </section>
  </main>;
}

function DraftSection({ title, section, accent = false }: { title: string; section: ReportSection | null; accent?: boolean }) {
  return <article className={`review-card${accent ? " review-card-accent" : ""}`}><h3>{title}</h3>
    <p>{section?.summary || "未提供"}</p>{section?.points.length ? <ul>{section.points.map((point) => <li key={point}>{point}</li>)}</ul> : null}</article>;
}

function ListSection({ title, items, compact = false }: { title: string; items: string[]; compact?: boolean }) {
  return <section className={compact ? "compact-list" : "review-card"}><h3>{title}</h3>
    {items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>未提供</p>}</section>;
}
