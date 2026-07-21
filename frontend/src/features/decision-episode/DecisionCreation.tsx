import { type FormEvent, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  decisionEpisodeApi,
  type DecisionEpisode,
} from "./decisionEpisodeApi";

type Props = {
  session: Session;
  episodeId: string;
  onBack: () => void;
  onCreated: (id: string) => void;
  onReady: (id: string) => void;
};

const lines = (value: string) => value.split("\n").map((item) => item.trim()).filter(Boolean);

export default function DecisionCreation({ session, episodeId, onBack, onCreated, onReady }: Props) {
  const [episode, setEpisode] = useState<DecisionEpisode | null>(null);
  const [title, setTitle] = useState("");
  const [question, setQuestion] = useState("");
  const [domain, setDomain] = useState("");
  const [importance, setImportance] = useState(3);
  const [background, setBackground] = useState("");
  const [goal, setGoal] = useState("");
  const [values, setValues] = useState("");
  const [facts, setFacts] = useState("");
  const [assumptions, setAssumptions] = useState("");
  const [unknowns, setUnknowns] = useState("");
  const [constraints, setConstraints] = useState("");
  const [options, setOptions] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(Boolean(episodeId));
  const [error, setError] = useState("");

  useEffect(() => {
    if (!episodeId) return;
    let active = true;
    setLoading(true);
    void decisionEpisodeApi.load(session, episodeId)
      .then((loaded) => {
        if (!active) return;
        setEpisode(loaded);
        setTitle(loaded.title);
        setQuestion(loaded.decision_question);
        setDomain(loaded.domain ?? "");
        setImportance(loaded.importance ?? 3);
        setBackground(loaded.background ?? "");
        setGoal(loaded.goal ?? "");
        setValues(loaded.values.join("\n"));
        setFacts(loaded.facts.join("\n"));
        setAssumptions(loaded.assumptions.join("\n"));
        setUnknowns(loaded.unknowns.join("\n"));
        setConstraints(loaded.constraints.join("\n"));
        setOptions(loaded.options.join("\n"));
      })
      .catch((cause) => { if (active) setError(message(cause)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [episodeId, session]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setSaving(true); setError("");
    try {
      const created = await decisionEpisodeApi.create(session, {
        title: title.trim(), decision_question: question.trim(),
        domain: domain.trim() || null, importance,
      });
      setEpisode(created);
      onCreated(created.id);
    } catch (cause) { setError(message(cause)); }
    finally { setSaving(false); }
  }

  async function saveBackground(event: FormEvent) {
    event.preventDefault();
    if (!episode) return;
    setSaving(true); setError("");
    try {
      const saved = await decisionEpisodeApi.update(session, episode.id, {
        background: background.trim(), goal: goal.trim() || null,
        values: lines(values), facts: lines(facts), assumptions: lines(assumptions),
        unknowns: lines(unknowns), constraints: lines(constraints), options: lines(options),
      });
      const ready = await decisionEpisodeApi.ready(session, saved.id);
      setEpisode(ready);
      onReady(ready.id);
    } catch (cause) { setError(message(cause)); }
    finally { setSaving(false); }
  }

  if (loading) return <main className="loading-screen">正在恢复决策事件…</main>;

  return <main className="decision-create-page">
    <header className="report-nav"><div className="brand"><span className="brand-mark">GA</span><span>Growth Atlas</span></div><button className="nav-back" onClick={onBack}>返回个人档案</button></header>
    <section className="decision-create-shell">
      <div className="decision-create-intro"><p className="eyebrow">DECISION EPISODE · {episode ? "02" : "01"}</p><h1>{episode ? "补充做决定所需的信息" : "创建一次正式决策"}</h1><p>{episode ? "先说明为什么现在要决定，再分别记录好结果的标准、已确认的信息、待验证的判断和现实限制。" : "先聚焦一个真实问题。系统会创建可恢复、可追踪的 Decision Episode。"}</p></div>
      {!episode ? <form className="reflection-form" onSubmit={create}>
        <label htmlFor="episode-title">事件标题</label><input id="episode-title" required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="例如：是否接受新的实习机会" />
        <label htmlFor="episode-question">你真正需要决定什么？</label><textarea id="episode-question" required minLength={3} maxLength={10000} value={question} onChange={(e) => setQuestion(e.target.value)} rows={6} />
        <label htmlFor="episode-domain">决策领域（可选）</label><input id="episode-domain" maxLength={100} value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="学业、职业、项目……" />
        <label htmlFor="episode-importance">重要程度：{importance}</label><input id="episode-importance" type="range" min="1" max="5" value={importance} onChange={(e) => setImportance(Number(e.target.value))} />
        {error && <p className="analysis-error">{error}</p>}<button className="primary-button analyze-button" disabled={saving}>{saving ? "正在创建…" : "创建 Decision Episode"}</button>
      </form> : episode.status === "ready_for_analysis" ? <section className="episode-ready-card"><h2>已进入 AI 分析准备状态</h2><p>本次决策背景已经保存，可以查看完整 Episode 详情。</p><button className="primary-button" onClick={() => onReady(episode.id)}>查看 Episode 详情</button></section> : <form className="reflection-form decision-canvas" onSubmit={saveBackground}>
        <div className="decision-canvas-note"><strong>先建立可审阅的判断基础</strong><p>需要填写多条答案时，请写完一条后按回车换行，再写下一条。已确认的信息写入“事实”；尚未证实的预测写入“待验证判断”。</p></div>
        <label htmlFor="episode-background">为什么现在需要做这个决定？</label><textarea id="episode-background" required maxLength={5000} value={background} onChange={(e) => setBackground(e.target.value)} rows={5} placeholder="用 2–3 句话说明：发生了什么、是否有截止时间、哪些人或事情受到影响。" />
        <label htmlFor="episode-goal">怎样才算一个好结果？</label><textarea id="episode-goal" required maxLength={3000} value={goal} onChange={(e) => setGoal(e.target.value)} rows={3} placeholder="例如：不延迟毕业，同时确认新专业是否真的适合我。先写结果标准，不要直接写选择哪个方案。" />
        <label htmlFor="episode-values">做取舍时，你最不愿牺牲什么？（可选，多项请按回车换行）</label><textarea id="episode-values" value={values} onChange={(e) => setValues(e.target.value)} rows={3} placeholder={"按时毕业\n真正感兴趣的学习方向\n未来就业选择"} />
        <label htmlFor="episode-facts">你已经确认了哪些信息？（至少一条，多条请按回车换行）</label><textarea id="episode-facts" required value={facts} onChange={(e) => setFacts(e.target.value)} rows={4} placeholder={"学校通知：今年转专业名额为 10 人\n培养方案显示：转专业后需要补修 4 门课"} />
        <label htmlFor="episode-assumptions">哪些判断目前还没有被证实？（可选，多条请按回车换行）</label><textarea id="episode-assumptions" value={assumptions} onChange={(e) => setAssumptions(e.target.value)} rows={3} placeholder={"我推测自己会更喜欢新专业的课程\n我认为补修课程不会导致延迟毕业"} />
        <label htmlFor="episode-unknowns">还需要查清什么，才能更有把握？（至少一条，多条请按回车换行）</label><textarea id="episode-unknowns" required value={unknowns} onChange={(e) => setUnknowns(e.target.value)} rows={4} placeholder={"新专业每周实际学习强度是多少\n往年转专业录取标准是什么"} />
        <label htmlFor="episode-constraints">哪些条件暂时无法改变？（可选，多条请按回车换行）</label><textarea id="episode-constraints" value={constraints} onChange={(e) => setConstraints(e.target.value)} rows={4} placeholder={"申请截止日期是 9 月 10 日\n本学期最多只能额外修 6 学分"} />
        <label htmlFor="episode-options">你现在可以选择哪些做法？（至少两种，每写一种后按回车换行）</label><textarea id="episode-options" required value={options} onChange={(e) => setOptions(e.target.value)} rows={4} placeholder={"申请转专业\n保留当前专业并辅修感兴趣的课程\n先咨询学长和老师，再决定是否申请"} />
        {error && <p className="analysis-error">{error}</p>}<button className="primary-button analyze-button" disabled={saving || !background.trim() || !goal.trim() || lines(facts).length < 1 || lines(unknowns).length < 1 || lines(options).length < 2}>{saving ? "正在保存…" : "保存判断基础并准备 AI 分析"}</button>
      </form>}
    </section>
  </main>;
}

function message(cause: unknown) { return cause instanceof Error ? cause.message : "操作失败，请稍后重试。"; }
