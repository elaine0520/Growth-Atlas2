import { FormEvent, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { actionFeedbackApi, type ActionPlan, type Feedback } from "./actionFeedbackApi";
import { decisionEpisodeApi, type DecisionEpisode } from "./decisionEpisodeApi";

type Props = { session: Session; episodeId: string; onBack: () => void; onMemory: (feedbackId: string) => void };

const lines = (value: string) => value.split("\n").map((item) => item.trim()).filter(Boolean);

export default function DecisionExecution({ session, episodeId, onBack, onMemory }: Props) {
  const [episode, setEpisode] = useState<DecisionEpisode | null>(null);
  const [plan, setPlan] = useState<ActionPlan | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [objective, setObjective] = useState("");
  const [actions, setActions] = useState("");
  const [criteria, setCriteria] = useState("");
  const [obstacles, setObstacles] = useState("");
  const [actualActions, setActualActions] = useState("");
  const [outcome, setOutcome] = useState("");
  const [comparison, setComparison] = useState("");
  const [lessons, setLessons] = useState("");

  useEffect(() => {
    let active = true;
    void decisionEpisodeApi.load(session, episodeId).then(async (loadedEpisode) => {
      if (!active) return;
      setEpisode(loadedEpisode);
      if (loadedEpisode.status !== "committed") {
        const loadedPlan = await actionFeedbackApi.loadPlan(session, episodeId);
        if (!active) return;
        setPlan(loadedPlan);
        setActualActions(loadedPlan.actions.filter((item) => item.status === "completed").map((item) => item.description).join("\n"));
        if (loadedEpisode.status === "reflected") {
          setFeedback(await actionFeedbackApi.loadFeedback(session, episodeId));
        }
      }
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : "无法加载执行记录");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [episodeId, session]);

  async function createPlan(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      const created = await actionFeedbackApi.createPlan(session, episodeId, {
        objective: objective.trim(), actions: lines(actions),
        success_criteria: criteria.trim() || null, major_obstacles: lines(obstacles),
      });
      setPlan(created);
      setEpisode((current) => current ? { ...current, status: "acting" } : current);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "行动计划创建失败"); }
    finally { setBusy(false); }
  }

  async function toggleAction(itemId: string, completed: boolean) {
    if (!plan) return;
    setBusy(true); setError("");
    try {
      const updated = await actionFeedbackApi.completeAction(session, episodeId, plan.id, itemId, completed);
      const nextItems = plan.actions.map((item) => item.id === itemId ? updated : item);
      setPlan({ ...plan, actions: nextItems });
      setActualActions(nextItems.filter((item) => item.status === "completed").map((item) => item.description).join("\n"));
      if (nextItems.every((item) => item.status === "completed")) {
        setEpisode((current) => current ? { ...current, status: "awaiting_feedback" } : current);
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "行动状态更新失败"); }
    finally { setBusy(false); }
  }

  async function submitFeedback(event: FormEvent) {
    event.preventDefault();
    if (!plan) return;
    setBusy(true); setError("");
    try {
      const submitted = await actionFeedbackApi.submitFeedback(session, episodeId, {
        action_plan_id: plan.id, actual_actions: lines(actualActions),
        actual_outcome: outcome.trim(), expected_vs_actual: comparison.trim(),
        lessons_learned: lines(lessons),
      });
      setFeedback(submitted);
      setEpisode((current) => current ? { ...current, status: "reflected" } : current);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "反馈提交失败"); }
    finally { setBusy(false); }
  }

  if (loading) return <main className="loading-screen">正在读取行动记录…</main>;
  if (!episode) return <main className="loading-screen">{error || "Decision Episode 不存在"}</main>;

  return <main className="execution-page">
    <header className="report-nav"><div className="brand"><span className="brand-mark">GA</span><span>Growth Atlas</span></div>
      <button className="nav-back" onClick={onBack}>返回决策详情</button></header>
    <section className="execution-hero"><p className="eyebrow">DECISION → ACTION → FEEDBACK</p>
      <h1>{episode.final_decision}</h1><p>{episode.decision_rationale}</p></section>
    <section className="execution-content">
      {error && <p className="form-message error">{error}</p>}
      {!plan && <PlanForm objective={objective} actions={actions} criteria={criteria} obstacles={obstacles}
        setObjective={setObjective} setActions={setActions} setCriteria={setCriteria}
        setObstacles={setObstacles} busy={busy} onSubmit={createPlan} />}
      {plan && <PlanView plan={plan} busy={busy} onToggle={toggleAction} />}
      {plan && !feedback && <FeedbackForm actualActions={actualActions} outcome={outcome}
        comparison={comparison} lessons={lessons} setActualActions={setActualActions}
        setOutcome={setOutcome} setComparison={setComparison} setLessons={setLessons}
        busy={busy} onSubmit={submitFeedback} />}
      {feedback && <FeedbackView feedback={feedback} onMemory={onMemory} />}
    </section>
  </main>;
}

type Setter = (value: string) => void;
function PlanForm(props: { objective: string; actions: string; criteria: string; obstacles: string; setObjective: Setter; setActions: Setter; setCriteria: Setter; setObstacles: Setter; busy: boolean; onSubmit: (event: FormEvent) => void }) {
  return <form className="execution-form" onSubmit={props.onSubmit}><p className="eyebrow">01 · ACTION PLAN</p><h2>把决定变成下一步</h2>
    <label>目标<textarea required value={props.objective} onChange={(e) => props.setObjective(e.target.value)} /></label>
    <label>行动步骤（每行一项）<textarea required value={props.actions} onChange={(e) => props.setActions(e.target.value)} /></label>
    <label>成功标准<textarea required value={props.criteria} onChange={(e) => props.setCriteria(e.target.value)} /></label>
    <label>主要障碍（每行一项）<textarea value={props.obstacles} onChange={(e) => props.setObstacles(e.target.value)} /></label>
    <button className="primary-button" disabled={props.busy || !props.objective.trim() || !lines(props.actions).length}>开始执行</button></form>;
}

function PlanView({ plan, busy, onToggle }: { plan: ActionPlan; busy: boolean; onToggle: (id: string, complete: boolean) => void }) {
  return <section className="execution-plan"><p className="eyebrow">01 · ACTION PLAN</p><h2>{plan.objective}</h2>
    <p><strong>成功标准：</strong>{plan.success_criteria || "未填写"}</p>
    {plan.major_obstacles.length > 0 && <p><strong>主要障碍：</strong>{plan.major_obstacles.join("；")}</p>}
    <div className="action-checklist">{plan.actions.map((item) => <label key={item.id}>
      <input type="checkbox" disabled={busy || plan.status === "completed"} checked={item.status === "completed"}
        onChange={(event) => void onToggle(item.id, event.target.checked)} /><span>{item.description}</span></label>)}</div></section>;
}

function FeedbackForm(props: { actualActions: string; outcome: string; comparison: string; lessons: string; setActualActions: Setter; setOutcome: Setter; setComparison: Setter; setLessons: Setter; busy: boolean; onSubmit: (event: FormEvent) => void }) {
  return <form className="execution-form feedback-form" onSubmit={props.onSubmit}><p className="eyebrow">02 · FEEDBACK</p><h2>记录现实发生了什么</h2>
    <label>实际完成的行动（每行一项）<textarea value={props.actualActions} onChange={(e) => props.setActualActions(e.target.value)} /></label>
    <label>实际结果<textarea required value={props.outcome} onChange={(e) => props.setOutcome(e.target.value)} /></label>
    <label>预期与实际的差异<textarea required value={props.comparison} onChange={(e) => props.setComparison(e.target.value)} /></label>
    <label>学到的经验（每行一项）<textarea required value={props.lessons} onChange={(e) => props.setLessons(e.target.value)} /></label>
    <button className="primary-button" disabled={props.busy || !props.outcome.trim() || !props.comparison.trim() || !lines(props.lessons).length}>提交反馈并完成复盘</button>
    <p className="review-note">本次提交只保存 Feedback，不会生成 Memory。</p></form>;
}

function FeedbackView({ feedback, onMemory }: { feedback: Feedback; onMemory: (id: string) => void }) {
  return <section className="feedback-complete"><p className="eyebrow">FEEDBACK CONFIRMED</p><h2>这次决策已经完成现实反馈</h2>
    <h3>实际结果</h3><p>{feedback.actual_outcome}</p><h3>预期与实际</h3><p>{feedback.expected_vs_actual}</p>
    <h3>学到的经验</h3><ul>{feedback.lessons_learned.map((lesson) => <li key={lesson}>{lesson}</li>)}</ul>
    <small>尚未生成任何 Decision Memory。</small>
    <button className="primary-button memory-next" onClick={() => onMemory(feedback.id)}>审阅并提取 Memory Candidate</button></section>;
}
