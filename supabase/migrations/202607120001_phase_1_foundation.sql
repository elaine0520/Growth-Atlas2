-- Growth Atlas Phase 1: identity, profiles, core schema, and row-level security.

create extension if not exists pgcrypto;

create type public.profile_status as enum ('draft', 'pending_confirmation', 'confirmed', 'archived');
create type public.conversation_status as enum ('active', 'completed', 'abandoned');
create type public.conversation_kind as enum ('profile_setup', 'reflection', 'review');
create type public.message_role as enum ('user', 'assistant', 'system');
create type public.reflection_status as enum ('draft', 'pending_confirmation', 'saved', 'reviewed', 'archived');
create type public.memory_status as enum ('suggested', 'confirmed', 'disabled', 'archived');
create type public.growth_dimension as enum (
  'self_awareness', 'emotional_regulation', 'decision_making',
  'execution', 'relationships', 'learning_growth'
);

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  nickname text check (char_length(nickname) <= 80),
  locale text not null default 'zh-CN' check (char_length(locale) <= 20),
  timezone text not null default 'Asia/Shanghai' check (char_length(timezone) <= 50),
  age_range text check (char_length(age_range) <= 50),
  life_stage text check (char_length(life_stage) <= 100),
  background text check (char_length(background) <= 2000),
  current_context text check (char_length(current_context) <= 2000),
  pressure_sources jsonb not null default '[]'::jsonb check (jsonb_typeof(pressure_sources) = 'array'),
  short_term_goals jsonb not null default '[]'::jsonb check (jsonb_typeof(short_term_goals) = 'array'),
  long_term_goals jsonb not null default '[]'::jsonb check (jsonb_typeof(long_term_goals) = 'array'),
  values_list jsonb not null default '[]'::jsonb check (jsonb_typeof(values_list) = 'array'),
  self_description jsonb not null default '[]'::jsonb check (jsonb_typeof(self_description) = 'array'),
  status public.profile_status not null default 'draft',
  version integer not null default 1 check (version > 0),
  privacy_version text,
  privacy_accepted_at timestamptz,
  memory_enabled boolean not null default false,
  allow_memory_suggestions boolean not null default false,
  retain_full_conversations boolean not null default false,
  confirmed_at timestamptz,
  last_reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  kind public.conversation_kind not null,
  status public.conversation_status not null default 'active',
  stage text not null default 'focus',
  title text check (char_length(title) <= 200),
  safety_state jsonb not null default '{}'::jsonb,
  retain_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.message_role not null,
  content text not null check (char_length(content) between 1 and 20000),
  sequence_no integer not null check (sequence_no >= 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (conversation_id, sequence_no)
);

create table public.reflections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  conversation_id uuid references public.conversations(id) on delete set null,
  title text not null check (char_length(title) between 1 and 200),
  user_question text not null check (char_length(user_question) between 1 and 5000),
  confirmed_facts jsonb not null default '[]'::jsonb,
  unknowns jsonb not null default '[]'::jsonb,
  emotions jsonb not null default '[]'::jsonb,
  insights jsonb not null default '[]'::jsonb,
  options jsonb not null default '[]'::jsonb,
  ai_analysis text,
  user_action jsonb,
  review jsonb,
  status public.reflection_status not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.analysis_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  reflection_id uuid not null references public.reflections(id) on delete cascade,
  content jsonb not null,
  model_name text,
  prompt_version text,
  confirmed_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.growth_scores (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  report_id uuid not null references public.analysis_reports(id) on delete cascade,
  dimension public.growth_dimension not null,
  evidence_status text not null default 'insufficient',
  trend text,
  summary text,
  evidence jsonb not null default '[]'::jsonb,
  user_feedback text,
  created_at timestamptz not null default now(),
  unique (report_id, dimension)
);

create table public.memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  content text not null check (char_length(content) between 1 and 5000),
  status public.memory_status not null default 'suggested',
  source_type text not null,
  source_id uuid,
  confidence text not null default 'ai_inference',
  confirmed_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index conversations_user_updated_idx on public.conversations (user_id, updated_at desc);
create index messages_conversation_sequence_idx on public.messages (conversation_id, sequence_no);
create index reflections_user_updated_idx on public.reflections (user_id, updated_at desc);
create index reports_user_created_idx on public.analysis_reports (user_id, created_at desc);
create index memories_user_status_idx on public.memories (user_id, status);

create function public.set_updated_at() returns trigger language plpgsql security invoker
set search_path = '' as $$ begin new.updated_at = now(); return new; end; $$;

create trigger profiles_set_updated_at before update on public.profiles
for each row execute function public.set_updated_at();
create trigger conversations_set_updated_at before update on public.conversations
for each row execute function public.set_updated_at();
create trigger reflections_set_updated_at before update on public.reflections
for each row execute function public.set_updated_at();
create trigger memories_set_updated_at before update on public.memories
for each row execute function public.set_updated_at();

create function public.handle_new_user() returns trigger language plpgsql security definer
set search_path = '' as $$
begin
  insert into public.profiles (id, nickname)
  values (new.id, nullif(new.raw_user_meta_data ->> 'nickname', ''));
  return new;
end;
$$;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.reflections enable row level security;
alter table public.analysis_reports enable row level security;
alter table public.growth_scores enable row level security;
alter table public.memories enable row level security;

create policy profiles_select_own on public.profiles for select to authenticated using ((select auth.uid()) = id);
create policy profiles_update_own on public.profiles for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

create policy conversations_own on public.conversations for all to authenticated
using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy messages_own on public.messages for all to authenticated
using ((select auth.uid()) = user_id) with check (
  (select auth.uid()) = user_id and exists (
    select 1 from public.conversations c where c.id = conversation_id and c.user_id = (select auth.uid())
  )
);
create policy reflections_own on public.reflections for all to authenticated
using ((select auth.uid()) = user_id) with check (
  (select auth.uid()) = user_id and (
    conversation_id is null or exists (
      select 1 from public.conversations c
      where c.id = conversation_id and c.user_id = (select auth.uid())
    )
  )
);
create policy reports_own on public.analysis_reports for all to authenticated
using ((select auth.uid()) = user_id) with check (
  (select auth.uid()) = user_id and exists (
    select 1 from public.reflections r where r.id = reflection_id and r.user_id = (select auth.uid())
  )
);
create policy scores_own on public.growth_scores for all to authenticated
using ((select auth.uid()) = user_id) with check (
  (select auth.uid()) = user_id and exists (
    select 1 from public.analysis_reports ar where ar.id = report_id and ar.user_id = (select auth.uid())
  )
);
create policy memories_own on public.memories for all to authenticated
using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

revoke all on all tables in schema public from anon;
grant usage on schema public to authenticated;
grant select, update on public.profiles to authenticated;
grant select, insert, update, delete on public.conversations, public.messages, public.reflections,
  public.analysis_reports, public.growth_scores, public.memories to authenticated;

-- Trigger functions are internal implementation details, not public RPCs.
revoke execute on function public.set_updated_at() from public, anon, authenticated;
revoke execute on function public.handle_new_user() from public, anon, authenticated;
