import { FormEvent, useState } from "react";
import { supabase } from "../../lib/supabase";

type Props = { onAuthenticated: () => void };

function AuthScreen({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [message, setMessage] = useState("");
  const [messageError, setMessageError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    setMessageError(false);
    try {
      const result = mode === "login"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({
            email,
            password,
            options: { data: { nickname: nickname.trim() || undefined } },
          });
      if (result.error) {
        setMessageError(true);
        setMessage(result.error.message);
      } else if (mode === "signup" && !result.data.session) {
        setMessage("注册成功，请前往邮箱完成验证后登录。");
      } else if (result.data.session) {
        onAuthenticated();
      }
    } catch {
      setMessageError(true);
      setMessage("暂时无法连接服务，请检查网络后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="brand-panel">
        <Brand />
        <div className="brand-message">
          <p className="eyebrow">GROWTH ATLAS</p>
          <h2>看清此刻，<br />走向下一步。</h2>
          <p>反思 · 洞察 · 决策 · 成长</p>
        </div>
        <p className="privacy-note">你的成长记录仅对你可见</p>
      </aside>
      <section className="form-panel auth-panel">
        <form className="auth-card" onSubmit={submit}>
          <p className="eyebrow">{mode === "login" ? "欢迎回来" : "开始建立你的成长地图"}</p>
          <h1>{mode === "login" ? "登录 Growth Atlas" : "创建账户"}</h1>
          {mode === "signup" && <><label className="field-label" htmlFor="nickname">昵称（可选）</label><input id="nickname" value={nickname} onChange={(e) => setNickname(e.target.value)} maxLength={80} /></>}
          <label className="field-label" htmlFor="email">邮箱</label>
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          <label className="field-label" htmlFor="password">密码</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} autoComplete={mode === "login" ? "current-password" : "new-password"} />
          {message && <p className="form-message" role={messageError ? "alert" : "status"}>{message}</p>}
          <button className="primary-button auth-submit" disabled={submitting}>{submitting ? "请稍候…" : mode === "login" ? "登录" : "注册"}</button>
          <button className="text-button auth-switch" type="button" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setMessage(""); setMessageError(false); }}>
            {mode === "login" ? "还没有账户？创建账户" : "已有账户？返回登录"}
          </button>
        </form>
      </section>
    </main>
  );
}

function Brand() { return <a className="brand" href="#top"><span className="brand-mark">GA</span><span>Growth Atlas</span></a>; }
export default AuthScreen;
