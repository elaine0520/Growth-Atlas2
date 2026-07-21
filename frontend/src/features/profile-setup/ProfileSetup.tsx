import { FormEvent, useCallback, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "../../lib/supabase";
import { IDENTITY_OPTIONS, VALUE_OPTIONS } from "./constants";
import { profileApi } from "./profileApi";
import {
  EMPTY_PROFILE_FORM,
  formToUpdate,
  recordToForm,
  type ProfileFormData,
  type ProfileRecord,
} from "./types";

type Props = { session: Session; onStartDecision: () => void; onOpenMemory: () => void; onOpenGrowthMap: () => void };
type ViewState = "loading" | "load-error" | "editing" | "confirmed";

function ProfileSetup({ session, onStartDecision, onOpenMemory, onOpenGrowthMap }: Props) {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<ProfileFormData>(EMPTY_PROFILE_FORM);
  const [profile, setProfile] = useState<ProfileRecord | null>(null);
  const [view, setView] = useState<ViewState>("loading");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadProfile = useCallback(async () => {
    setView("loading");
    setError("");
    try {
      const loaded = await profileApi.load(session);
      setProfile(loaded);
      setForm(recordToForm(loaded));
      setView(loaded.status === "confirmed" ? "confirmed" : "editing");
    } catch (reason) {
      setError(errorMessage(reason, "档案加载失败，请检查网络后重试。"));
      setView("load-error");
    }
  }, [session]);

  useEffect(() => { void loadProfile(); }, [loadProfile]);

  function set<K extends keyof ProfileFormData>(key: K, value: ProfileFormData[K]) {
    setForm((old) => ({ ...old, [key]: value }));
  }

  function toggleValue(value: string) {
    set("values", form.values.includes(value)
      ? form.values.filter((item) => item !== value)
      : [...form.values, value]);
  }

  async function saveDraft() {
    setSaving(true);
    setError("");
    try {
      const saved = await profileApi.save(session, formToUpdate(form));
      setProfile(saved);
      setForm(recordToForm(saved));
      return saved;
    } catch (reason) {
      setError(errorMessage(reason, "保存失败，请稍后重试。"));
      throw reason;
    } finally {
      setSaving(false);
    }
  }

  async function submitStep(event: FormEvent) {
    event.preventDefault();
    if (step < 3) {
      try {
        await saveDraft();
        setStep((value) => value + 1);
      } catch { /* Error is shown inline. */ }
      return;
    }

    const validationError = validateForConfirmation(form);
    if (validationError) {
      setError(validationError);
      return;
    }
    try {
      await saveDraft();
      const confirmed = await profileApi.confirm(session);
      setProfile(confirmed);
      setForm(recordToForm(confirmed));
      setView("confirmed");
    } catch (reason) {
      setError(errorMessage(reason, "确认失败，请稍后重试。"));
    }
  }

  async function signOut() {
    setError("");
    const { error: signOutError } = await supabase.auth.signOut({ scope: "local" });
    if (signOutError) setError("退出失败，请重试。");
  }

  if (view === "loading") return <main className="loading-screen">正在读取你的档案…</main>;

  if (view === "load-error") {
    return (
      <main className="loading-screen load-error-screen">
        <p className="form-message error" role="alert">{error}</p>
        <button className="primary-button" onClick={() => void loadProfile()}>重新加载</button>
        <button className="text-button" onClick={() => void signOut()}>退出登录</button>
      </main>
    );
  }

  if (view === "confirmed" && profile) {
    return (
      <main className="app-shell">
        <ProfileAside onSignOut={signOut} />
        <section className="form-panel profile-ready-panel">
          <section className="completion-card">
            <div className="completion-mark">✓</div>
            <p className="eyebrow">个人档案已保存</p>
            <h1>{profile.user_info.nickname ? `${profile.user_info.nickname}，继续向前` : "从一个真实的困惑开始"}</h1>
            <div className="profile-summary">
              <SummaryItem label="当前身份" value={profile.user_info.life_stage} />
              <SummaryItem label="近期生活重心" value={profile.current_context} />
              <SummaryItem label="成长目标" value={[...profile.short_term_goals, ...profile.long_term_goals].join(" · ")} />
              <SummaryItem label="优先保住的价值" value={profile.values.join(" · ")} />
            </div>
            <p className="saved-note">最后保存：{formatDate(profile.updated_at)}</p>
            <button className="primary-button" onClick={onStartDecision}>创建一次正式决策 <span>→</span></button>
            <button className="text-button profile-reset" onClick={onOpenGrowthMap}>查看 Decision Timeline</button>
            <button className="text-button profile-reset" onClick={onOpenMemory}>管理 Decision Memory</button>
            <button className="text-button profile-reset" onClick={() => { setStep(0); setError(""); setView("editing"); }}>编辑个人档案</button>
            {error && <p className="form-message error" role="alert">{error}</p>}
          </section>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <ProfileAside onSignOut={signOut} />
      <section className="form-panel">
        <header className="progress-header">
          <button type="button" aria-label="返回上一步" className="back-button" disabled={step === 0 || saving} onClick={() => setStep(step - 1)}>←</button>
          <div className="progress-copy"><span>个人档案</span><span>{step + 1} / 4</span><div className="progress-track"><div className="progress-value" style={{ width: `${(step + 1) * 25}%` }} /></div></div>
        </header>
        <div className="form-content">
          <form className="form-step" onSubmit={submitStep}>
            {step === 0 && <StepIdentity form={form} set={set} />}
            {step === 1 && <StepContext form={form} set={set} />}
            {step === 2 && <StepGoals form={form} set={set} />}
            {step === 3 && <StepValues form={form} set={set} toggleValue={toggleValue} />}
            {error && <p className="form-message error" role="alert">{error}</p>}
            <div className="step-actions">
              <button className="text-button" type="button" disabled={step === 0 || saving} onClick={() => setStep(step - 1)}>上一步</button>
              <button className="primary-button" type="submit" disabled={saving}>{saving ? "保存中…" : step < 3 ? "保存并继续" : "保存并确认档案"}{step < 3 && <span>→</span>}</button>
            </div>
          </form>
        </div>
      </section>
    </main>
  );
}

type SetField = <K extends keyof ProfileFormData>(key: K, value: ProfileFormData[K]) => void;

function StepIdentity({ form, set }: { form: ProfileFormData; set: SetField }) {
  return <><Heading number="01" title="先认识此刻的你" text="只填写你愿意提供、且有助于后续分析的信息。" /><label className="field-label" htmlFor="nickname">希望怎样称呼你？</label><input id="nickname" name="nickname" value={form.nickname} maxLength={80} autoComplete="nickname" onChange={(e) => set("nickname", e.target.value)} /><label className="field-label" htmlFor="age-range">年龄阶段</label><input id="age-range" name="ageRange" value={form.ageRange} maxLength={50} placeholder="例如：18–22 岁" onChange={(e) => set("ageRange", e.target.value)} /><fieldset><legend>当前身份（确认档案前必填）</legend><div className="identity-grid">{IDENTITY_OPTIONS.map((item) => <button type="button" className={`choice-chip ${form.lifeStage === item ? "selected" : ""}`} aria-pressed={form.lifeStage === item} onClick={() => set("lifeStage", item)} key={item}>{item}</button>)}</div></fieldset><label className="field-label" htmlFor="background">其他背景（可选）</label><textarea id="background" name="background" value={form.background} maxLength={2000} rows={3} onChange={(e) => set("background", e.target.value)} /></>;
}

function StepContext({ form, set }: { form: ProfileFormData; set: SetField }) {
  return <><Heading number="02" title="你最近的生活重心是什么？" text="不用概括整个人生，只描述未来几个月最需要你投入时间和精力的事情。" /><label className="field-label" htmlFor="current-context">最近主要在处理什么？（确认档案前必填）</label><textarea id="current-context" name="currentContext" value={form.currentContext} maxLength={2000} rows={5} placeholder="例如：大三下学期，正在决定是否转专业，同时要准备期末考试。" onChange={(e) => set("currentContext", e.target.value)} /><label className="field-label" htmlFor="pressure-sources">哪些事情正在给你压力？（如有多项，请按回车换行）</label><textarea id="pressure-sources" name="pressureSources" value={form.pressureSources} rows={4} placeholder={"转专业名额有限\n担心延迟毕业\n家人希望我保持现有专业"} onChange={(e) => set("pressureSources", e.target.value)} /></>;
}

function StepGoals({ form, set }: { form: ProfileFormData; set: SetField }) {
  return <><Heading number="03" title="你想走向哪里？" text="至少填写一个近期目标或长期方向，之后可以随时调整。" /><label className="field-label" htmlFor="short-term-goals">未来 3–12 个月想完成什么？（多项目标请按回车换行）</label><textarea id="short-term-goals" name="shortTermGoals" value={form.shortTermGoals} rows={4} placeholder={"完成转专业申请\n把专业课成绩提升到前 30%"} onChange={(e) => set("shortTermGoals", e.target.value)} /><label className="field-label" htmlFor="long-term-goals">未来几年希望靠近什么方向？（多个方向请按回车换行）</label><textarea id="long-term-goals" name="longTermGoals" value={form.longTermGoals} rows={4} placeholder="例如：找到兼顾兴趣与就业空间的专业方向" onChange={(e) => set("longTermGoals", e.target.value)} /></>;
}

function StepValues({ form, set, toggleValue }: { form: ProfileFormData; set: SetField; toggleValue: (value: string) => void }) {
  return <><Heading number="04" title="做选择时，你更不愿牺牲什么？" text="想象两个方案不能兼得时，你会优先保住什么。至少选择一项，没有标准答案。" /><fieldset><legend className="sr-only">重要取舍（确认档案前必填）</legend><div className="value-grid">{VALUE_OPTIONS.map((item) => <button type="button" key={item.label} className={`value-card ${form.values.includes(item.label) ? "selected" : ""}`} aria-pressed={form.values.includes(item.label)} onClick={() => toggleValue(item.label)}><strong>{item.label}</strong><small>{item.hint}</small><span className="value-check">✓</span></button>)}</div></fieldset><label className="field-label" htmlFor="self-description">哪些具体描述符合现在的你？（可选，多条描述请按回车换行）</label><textarea id="self-description" name="selfDescription" value={form.selfDescription} rows={5} placeholder={"我在目标明确时更容易行动\n面对不确定性时，我会先收集很多信息\n我目前最想改善的是时间安排"} onChange={(e) => set("selfDescription", e.target.value)} /></>;
}

function ProfileAside({ onSignOut }: { onSignOut: () => Promise<void> }) {
  return <aside className="brand-panel"><Brand /><div className="brand-message"><p className="eyebrow">PERSONAL GROWTH PROFILE</p><h2>你的成长档案，<br />会随你一起变化。</h2><p>反思 · 洞察 · 决策 · 成长</p></div><button className="text-button sign-out" onClick={() => void onSignOut()}>退出登录</button></aside>;
}

function SummaryItem({ label, value }: { label: string; value: string | null }) {
  return <div><span>{label}</span><strong>{value || "尚未填写"}</strong></div>;
}

function validateForConfirmation(form: ProfileFormData) {
  if (!form.lifeStage) return "请返回第 1 步选择当前身份。";
  if (!form.currentContext.trim()) return "请返回第 2 步，填写最近主要在处理的事情。";
  if (!form.shortTermGoals.trim() && !form.longTermGoals.trim()) return "请返回第 3 步填写至少一个成长目标。";
  if (form.values.length === 0) return "请至少选择一项重要价值。";
  return "";
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "刚刚" : new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function errorMessage(reason: unknown, fallback: string) {
  return reason instanceof Error && reason.message ? reason.message : fallback;
}

function Heading({ number, title, text }: { number: string; title: string; text: string }) { return <header className="step-heading"><span>{number}</span><h1>{title}</h1><p>{text}</p></header>; }
function Brand() { return <a className="brand" href="#top"><span className="brand-mark">GA</span><span>Growth Atlas</span></a>; }
export default ProfileSetup;
