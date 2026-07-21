import { FormEvent, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  memoryApi,
  type DecisionMemory,
  type MemoryCandidate,
  type MemoryType,
} from "./memoryApi";

type Props = { session: Session; feedbackId?: string; onBack: () => void };
const lines = (value: string) => value.split("\n").map((item) => item.trim()).filter(Boolean);
const TYPE_LABELS: Record<MemoryType, string> = {
  decision_experience: "决策经验", confirmed_lesson: "确认的经验",
  effective_strategy: "有效策略", known_constraint: "已知约束",
  decision_pattern: "决策模式", profile_change: "档案变化",
};

export default function MemoryPage({ session, feedbackId, onBack }: Props) {
  const [candidates, setCandidates] = useState<MemoryCandidate[]>([]);
  const [memories, setMemories] = useState<DecisionMemory[]>([]);
  const [type, setType] = useState<MemoryType>("confirmed_lesson");
  const [content, setContent] = useState("");
  const [rationale, setRationale] = useState("");
  const [domains, setDomains] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void Promise.all([memoryApi.listCandidates(session), memoryApi.list(session)])
      .then(([nextCandidates, nextMemories]) => {
        if (active) { setCandidates(nextCandidates); setMemories(nextMemories); }
      }).catch((cause) => { if (active) setError(message(cause)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session]);

  async function createCandidate(event: FormEvent) {
    event.preventDefault();
    if (!feedbackId) return;
    setBusy(true); setError("");
    try {
      const created = await memoryApi.createCandidate(session, {
        feedback_id: feedbackId, candidate_type: type,
        proposed_content: content.trim(), rationale: rationale.trim(),
        applicable_domains: lines(domains),
      });
      setCandidates((current) => [created, ...current]);
      setContent(""); setRationale(""); setDomains("");
    } catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }

  async function confirm(candidate: MemoryCandidate, editedContent: string, editedDomains: string) {
    setBusy(true); setError("");
    try {
      const created = await memoryApi.confirmCandidate(
        session, candidate.id, editedContent.trim(), lines(editedDomains),
      );
      setCandidates((current) => current.filter((item) => item.id !== candidate.id));
      setMemories((current) => [created, ...current]);
    } catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }

  async function reject(id: string) {
    setBusy(true); setError("");
    try {
      await memoryApi.rejectCandidate(session, id);
      setCandidates((current) => current.filter((item) => item.id !== id));
    } catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }

  async function toggle(memory: DecisionMemory) {
    setBusy(true); setError("");
    try {
      const updated = await memoryApi.setStatus(
        session, memory.id, memory.status === "disabled" ? "active" : "disabled",
      );
      setMemories((current) => current.map((item) => item.id === memory.id ? updated : item));
    } catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }

  async function remove(id: string) {
    if (!window.confirm("确定删除这条 Decision Memory？删除后不会再用于未来分析。")) return;
    setBusy(true); setError("");
    try {
      await memoryApi.delete(session, id);
      setMemories((current) => current.filter((item) => item.id !== id));
    } catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }

  if (loading) return <main className="loading-screen">正在读取 Decision Memory…</main>;
  return <main className="memory-page">
    <header className="report-nav"><div className="brand"><span className="brand-mark">GA</span><span>Growth Atlas</span></div>
      <button className="nav-back" onClick={onBack}>返回</button></header>
    <section className="memory-hero"><p className="eyebrow">USER-CONFIRMED MEMORY</p><h1>Decision Memory</h1>
      <p>只有你明确确认的经验才会成为长期记忆。Candidate 不会被用于未来分析。</p></section>
    <section className="memory-content">
      {error && <p className="form-message error">{error}</p>}
      {feedbackId && <form className="memory-create" onSubmit={createCandidate}>
        <p className="eyebrow">FROM CONFIRMED FEEDBACK</p><h2>提出一条 Memory Candidate</h2>
        <label>类型<select value={type} onChange={(event) => setType(event.target.value as MemoryType)}>
          {Object.entries(TYPE_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
        <label>可能值得记住的经验<textarea required value={content} onChange={(e) => setContent(e.target.value)} /></label>
        <label>为什么可能值得长期保留<textarea required value={rationale} onChange={(e) => setRationale(e.target.value)} /></label>
        <label>适用领域（每行一项）<textarea value={domains} onChange={(e) => setDomains(e.target.value)} /></label>
        <button className="primary-button" disabled={busy || !content.trim() || !rationale.trim()}>创建 Candidate，不写入长期记忆</button>
      </form>}

      <section><p className="eyebrow">PENDING REVIEW</p><h2>待你确认的 Candidate</h2>
        {candidates.length ? <div className="memory-grid">{candidates.map((candidate) =>
          <CandidateCard key={candidate.id} candidate={candidate} busy={busy} onConfirm={confirm} onReject={reject} />)}</div>
          : <p className="memory-empty">目前没有待确认 Candidate。</p>}</section>

      <section><p className="eyebrow">LONG-TERM MEMORY</p><h2>已确认的 Decision Memory</h2>
        {memories.length ? <div className="memory-grid">{memories.map((memory) => <article className={`memory-card ${memory.status === "disabled" ? "memory-disabled" : ""}`} key={memory.id}>
          <div className="memory-card-head"><span>{TYPE_LABELS[memory.memory_type]}</span><strong>{memory.status}</strong></div>
          <p>{memory.content}</p><Evidence evidence={memory.evidence} />
          <div className="memory-actions"><button disabled={busy} onClick={() => void toggle(memory)}>{memory.status === "disabled" ? "重新启用" : "禁用"}</button>
            <button className="danger-button" disabled={busy} onClick={() => void remove(memory.id)}>删除</button></div>
        </article>)}</div> : <p className="memory-empty">尚未确认任何长期 Decision Memory。</p>}</section>
    </section>
  </main>;
}

function CandidateCard({ candidate, busy, onConfirm, onReject }: { candidate: MemoryCandidate; busy: boolean; onConfirm: (candidate: MemoryCandidate, content: string, domains: string) => Promise<void>; onReject: (id: string) => Promise<void> }) {
  const [content, setContent] = useState(candidate.proposed_content);
  const [domains, setDomains] = useState(candidate.applicable_domains.join("\n"));
  return <article className="memory-card candidate-card"><div className="memory-card-head"><span>{TYPE_LABELS[candidate.candidate_type]}</span><strong>Candidate</strong></div>
    <label>确认前可修改<textarea value={content} onChange={(e) => setContent(e.target.value)} /></label>
    <label>适用领域<textarea value={domains} onChange={(e) => setDomains(e.target.value)} /></label>
    <p className="candidate-rationale">提出理由：{candidate.rationale}</p><Evidence evidence={candidate.evidence} />
    <div className="memory-actions"><button className="primary-button" disabled={busy || !content.trim()} onClick={() => void onConfirm(candidate, content, domains)}>我确认写入长期 Memory</button>
      <button disabled={busy} onClick={() => void onReject(candidate.id)}>拒绝</button></div></article>;
}

function Evidence({ evidence }: { evidence: MemoryCandidate["evidence"] }) {
  return <div className="memory-evidence"><strong>来源与证据</strong>{evidence.map((item, index) =>
    <span key={`${item.source_type}-${item.source_id}-${index}`}>{item.source_type} · {item.note || item.source_id}</span>)}</div>;
}

function message(cause: unknown) { return cause instanceof Error ? cause.message : "Memory 操作失败"; }
