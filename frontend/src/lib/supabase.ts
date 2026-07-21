import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabaseConfigurationError = !url || !key
  ? "缺少前端身份服务配置。请联系部署管理员。"
  : null;

// Keep module initialization renderable so App can show a safe configuration page.
// No request is made while supabaseConfigurationError is present.
export const supabase = createClient(
  url || "http://127.0.0.1:54321",
  key || "missing-public-anon-key",
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  },
);
