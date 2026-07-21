import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  readGrowthMap,
  type ConfirmedExperience,
  type DecisionTimelineEntry,
  type GrowthMap,
} from "./growthMapApi";

type Props = { session: Session; onBack: () => void; onOpenEpisode: (id: string) => void };

export default function DecisionTimeline({ session, onBack, onOpenEpisode }: Props) {
  const [growthMap, setGrowthMap] = useState<GrowthMap | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void readGrowthMap(session)
      .then((result) => { if (active) setGrowthMap(result); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "读取失败"); });
    return () => { active = false; };
  }, [session]);

  return <main className="timeline-page growth-map-page">
    <header className="report-nav">
      <div className="brand"><span className="brand-mark">GA</span><span>Growth Atlas</span></div>
      <button className="nav-back" type="button" onClick={onBack}>返回</button>
    </header>
    <section className="timeline-hero"><p className="eyebrow">GROWTH MAP · FOUNDATION</p>
      <h1>你的决策演化轨迹</h1><p>这里不评价人格，也不计算成长分数。它只呈现你做过的决定、采取的行动、现实反馈和亲自确认的经验。</p></section>

    {error && <section className="timeline-list"><p className="analysis-error">{error}</p></section>}
    {!error && !growthMap && <section className="timeline-list"><p className="timeline-state">正在读取 Decision Timeline…</p></section>}
    {growthMap && <>
      <ExperienceSection experiences={growthMap.confirmed_experiences} />
      <section className="timeline-list" aria-label="Decision Episode 生命周期">
        <div className="growth-map-heading"><p className="eyebrow">DECISION TIMELINE</p><h2>从问题到经验</h2></div>
        {growthMap.timeline.length === 0 && <div className="timeline-empty"><h2>还没有 Decision Episode</h2><p>完成一次正式决策后，它的生命周期会出现在这里。</p></div>}
        {growthMap.timeline.map((item, index) => <TimelineEpisode item={item} index={index} onOpen={onOpenEpisode} key={item.id} />)}
      </section>
    </>}
  </main>;
}

function ExperienceSection({ experiences }: { experiences: ConfirmedExperience[] }) {
  return <section className="confirmed-experiences"><div className="growth-map-heading">
    <p className="eyebrow">CONFIRMED EXPERIENCES</p><h2>你确认值得保留的经验</h2>
    <p>仅展示经过你确认的 Decision Memory，不生成模式判断。</p></div>
    {experiences.length ? <div className="experience-grid">{experiences.map((item) =>
      <article className={item.status === "disabled" ? "experience-card experience-disabled" : "experience-card"} key={item.id}>
        <span>{item.memory_type.replaceAll("_", " ")} · {item.status}</span><p>{item.content}</p>
        {item.applicable_domains.length > 0 && <small>适用领域：{item.applicable_domains.join(" · ")}</small>}
      </article>)}</div> : <p className="memory-empty">尚未确认长期经验。</p>}
  </section>;
}

function TimelineEpisode({ item, index, onOpen }: { item: DecisionTimelineEntry; index: number; onOpen: (id: string) => void }) {
  return <article className="timeline-item">
    <div className="timeline-marker"><span>{String(index + 1).padStart(2, "0")}</span><i /></div>
    <div className="timeline-card lifecycle-card">
      <div className="lifecycle-card-head"><time dateTime={item.created_at}>{formatDate(item.created_at)}</time><strong>{item.status}</strong></div>
      <h2>{item.title}</h2><p className="timeline-question">“{item.decision_question}”</p>
      <div className="lifecycle-stages">
        <LifecycleStage number="01" title="Decision" active={Boolean(item.final_decision)}>
          <p>{item.final_decision || "尚未由用户确认最终决定"}</p>
          {item.decision_rationale && <small>{item.decision_rationale}</small>}
        </LifecycleStage>
        <LifecycleStage number="02" title="Action" active={Boolean(item.action_plan)}>
          {item.action_plan ? <><p>{item.action_plan.objective}</p>
            <small>{item.action_plan.actions.filter((action) => action.status === "completed").length} / {item.action_plan.actions.length} 项行动完成</small></> : <p>尚无行动计划</p>}
        </LifecycleStage>
        <LifecycleStage number="03" title="Feedback" active={item.feedback.length > 0}>
          {item.feedback.length ? item.feedback.map((feedback) => <div key={feedback.id}><p>{feedback.actual_outcome || "已提交反馈"}</p>
            {feedback.lessons_learned.length > 0 && <small>经验：{feedback.lessons_learned.join("；")}</small>}</div>) : <p>尚无现实反馈</p>}
        </LifecycleStage>
        <LifecycleStage number="04" title="Memory" active={item.confirmed_experiences.length > 0}>
          {item.confirmed_experiences.length ? item.confirmed_experiences.map((memory) => <p key={memory.id}>{memory.content}</p>) : <p>尚无用户确认的长期经验</p>}
        </LifecycleStage>
      </div>
      <button className="primary-button" type="button" onClick={() => onOpen(item.id)}>查看完整 Decision Episode <span>→</span></button>
    </div>
  </article>;
}

function LifecycleStage({ number, title, active, children }: { number: string; title: string; active: boolean; children: React.ReactNode }) {
  return <section className={active ? "lifecycle-stage lifecycle-stage-active" : "lifecycle-stage"}>
    <header><span>{number}</span><h3>{title}</h3></header>{children}</section>;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "long", timeStyle: "short" }).format(new Date(value));
}
