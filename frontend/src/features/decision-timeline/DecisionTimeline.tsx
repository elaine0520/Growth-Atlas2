import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { readDecisionTimeline, type DecisionTimelineItem } from "../reflection/decisionReport";

type Props = { session: Session; onBack: () => void; onOpenReport: (id: string) => void };

export default function DecisionTimeline({ session, onBack, onOpenReport }: Props) {
  const [items, setItems] = useState<DecisionTimelineItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void readDecisionTimeline(session)
      .then((result) => { if (active) setItems(result); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "读取失败"); });
    return () => { active = false; };
  }, [session]);

  return <main className="timeline-page">
    <header className="report-nav">
      <div className="brand"><span className="brand-mark">GA</span><span>Growth Atlas</span></div>
      <button className="nav-back" type="button" onClick={onBack}>返回 Reflection</button>
    </header>
    <section className="timeline-hero"><p className="eyebrow">DECISION HISTORY</p><h1>你的决策时间线</h1><p>按时间回看每一次选择、判断与行动方向。</p></section>
    <section className="timeline-list" aria-label="决策历史">
      {error && <p className="analysis-error">{error}</p>}
      {!error && items === null && <p className="timeline-state">正在读取决策历史…</p>}
      {items?.length === 0 && <div className="timeline-empty"><h2>还没有历史报告</h2><p>完成第一次 Reflection 后，报告会出现在这里。</p></div>}
      {items?.map((item, index) => <article className="timeline-item" key={item.id}>
        <div className="timeline-marker"><span>{String(index + 1).padStart(2, "0")}</span><i /></div>
        <div className="timeline-card">
          <time dateTime={item.created_at}>{new Intl.DateTimeFormat("zh-CN", { dateStyle: "long", timeStyle: "short" }).format(new Date(item.created_at))}</time>
          <h2>{item.question}</h2><p>{item.decision_summary}</p>
          <button className="primary-button" type="button" onClick={() => onOpenReport(item.id)}>查看历史报告 <span>→</span></button>
        </div>
      </article>)}
    </section>
  </main>;
}
