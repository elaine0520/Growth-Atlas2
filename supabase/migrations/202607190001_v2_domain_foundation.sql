-- Growth Atlas V2 domain foundation.
-- Adds the Personal Decision System data model without deleting V1 data.

create type public.v2_profile_status as enum (
  'draft', 'pending_confirmation', 'confirmed', 'superseded', 'archived'
);
create type public.v2_decision_episode_status as enum (
  'capturing', 'ready_for_analysis', 'analyzing', 'draft_ready',
  'awaiting_user_decision', 'committed', 'acting', 'awaiting_feedback',
  'reflected', 'archived', 'analysis_failed', 'cancelled', 'abandoned'
);
create type public.v2_report_draft_status as enum (
  'generating', 'ready', 'accepted', 'rejected', 'superseded', 'invalid',
  'generation_failed'
);
create type public.v2_action_plan_status as enum (
  'draft', 'confirmed', 'in_progress', 'completed', 'abandoned', 'superseded'
);
create type public.v2_action_item_status as enum (
  'pending', 'in_progress', 'completed', 'skipped'
);
create type public.v2_feedback_status as enum (
  'draft', 'pending_confirmation', 'confirmed', 'corrected', 'archived'
);
create type public.v2_feedback_type as enum (
  'checkpoint', 'outcome', 'reflection', 'final_review'
);
create type public.v2_memory_candidate_status as enum (
  'suggested', 'edited', 'confirmed', 'rejected', 'expired'
);
create type public.v2_decision_memory_status as enum (
  'active', 'needs_review', 'superseded', 'disabled', 'archived', 'deleted'
);
create type public.v2_memory_type as enum (
  'decision_experience', 'confirmed_lesson', 'effective_strategy',
  'known_constraint', 'decision_pattern', 'profile_change'
);

create table public.personal_decision_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  schema_version text not null default '2.0' check (schema_version = '2.0'),
  status public.v2_profile_status not null default 'draft',
  current_version integer not null default 1 check (current_version > 0),
  confirmed_version integer check (confirmed_version is null or confirmed_version > 0),
  current_version_id uuid,
  confirmed_version_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_reviewed_at timestamptz,
  unique (user_id),
  unique (id, user_id),
  check (confirmed_version is null or confirmed_version <= current_version),
  check (
    status <> 'confirmed'
    or (confirmed_version is not null and confirmed_version_id is not null)
  )
);

create table public.decision_profile_versions (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  schema_version text not null default '2.0' check (schema_version = '2.0'),
  version integer not null check (version > 0),
  status public.v2_profile_status not null default 'draft',
  stable_profile jsonb not null default '{}'::jsonb
    check (jsonb_typeof(stable_profile) = 'object'),
  dynamic_context jsonb not null default '{}'::jsonb
    check (jsonb_typeof(dynamic_context) = 'object'),
  decision_style jsonb not null default '[]'::jsonb
    check (jsonb_typeof(decision_style) = 'array'),
  supersedes_version_id uuid,
  confirmed_at timestamptz,
  last_reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (profile_id, user_id)
    references public.personal_decision_profiles(id, user_id) on delete cascade,
  foreign key (supersedes_version_id, user_id)
    references public.decision_profile_versions(id, user_id),
  unique (profile_id, version),
  unique (id, user_id),
  check (status <> 'confirmed' or confirmed_at is not null)
);

alter table public.personal_decision_profiles
  add foreign key (current_version_id, user_id)
    references public.decision_profile_versions(id, user_id),
  add foreign key (confirmed_version_id, user_id)
    references public.decision_profile_versions(id, user_id);

create table public.decision_episodes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  profile_version_id uuid,
  schema_version text not null default '2.0' check (schema_version = '2.0'),
  title text not null check (char_length(title) between 1 and 200),
  decision_question text not null check (char_length(decision_question) between 3 and 10000),
  domain text check (domain is null or char_length(domain) between 1 and 100),
  importance smallint check (importance between 1 and 5),
  context_snapshot jsonb check (
    context_snapshot is null or jsonb_typeof(context_snapshot) = 'object'
  ),
  goal text check (goal is null or char_length(goal) <= 3000),
  values_data jsonb not null default '[]'::jsonb check (jsonb_typeof(values_data) = 'array'),
  facts jsonb not null default '[]'::jsonb check (jsonb_typeof(facts) = 'array'),
  assumptions jsonb not null default '[]'::jsonb check (jsonb_typeof(assumptions) = 'array'),
  unknowns jsonb not null default '[]'::jsonb check (jsonb_typeof(unknowns) = 'array'),
  constraints_data jsonb not null default '[]'::jsonb
    check (jsonb_typeof(constraints_data) = 'array'),
  options jsonb not null default '[]'::jsonb check (jsonb_typeof(options) = 'array'),
  final_decision text check (final_decision is null or char_length(final_decision) <= 5000),
  decision_rationale text check (
    decision_rationale is null or char_length(decision_rationale) <= 5000
  ),
  evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(evidence) = 'array'),
  status public.v2_decision_episode_status not null default 'capturing',
  committed_at timestamptz,
  closed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (profile_version_id, user_id)
    references public.decision_profile_versions(id, user_id),
  unique (id, user_id),
  check (
    status not in ('committed', 'acting', 'awaiting_feedback', 'reflected')
    or (committed_at is not null and final_decision is not null)
  ),
  check (closed_at is null or committed_at is null or closed_at >= committed_at)
);

create table public.decision_report_drafts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  decision_episode_id uuid not null,
  schema_version text not null default '2.0' check (schema_version = '2.0'),
  version integer not null default 1 check (version > 0),
  status public.v2_report_draft_status not null default 'generating',
  goal_clarification jsonb check (
    goal_clarification is null or jsonb_typeof(goal_clarification) = 'object'
  ),
  values_analysis jsonb check (
    values_analysis is null or jsonb_typeof(values_analysis) = 'object'
  ),
  facts_analysis jsonb check (
    facts_analysis is null or jsonb_typeof(facts_analysis) = 'object'
  ),
  assumptions jsonb not null default '[]'::jsonb check (jsonb_typeof(assumptions) = 'array'),
  uncertainty jsonb not null default '[]'::jsonb check (jsonb_typeof(uncertainty) = 'array'),
  constraints_analysis jsonb check (
    constraints_analysis is null or jsonb_typeof(constraints_analysis) = 'object'
  ),
  options jsonb not null default '[]'::jsonb check (jsonb_typeof(options) = 'array'),
  recommendation jsonb check (
    recommendation is null or jsonb_typeof(recommendation) = 'object'
  ),
  recommendation_conditions jsonb not null default '[]'::jsonb
    check (jsonb_typeof(recommendation_conditions) = 'array'),
  change_conditions jsonb not null default '[]'::jsonb
    check (jsonb_typeof(change_conditions) = 'array'),
  proposed_action_plan jsonb check (
    proposed_action_plan is null or jsonb_typeof(proposed_action_plan) = 'object'
  ),
  feedback_plan jsonb check (feedback_plan is null or jsonb_typeof(feedback_plan) = 'object'),
  model_provider text check (model_provider is null or char_length(model_provider) <= 100),
  model_name text check (model_name is null or char_length(model_name) <= 100),
  prompt_version text check (prompt_version is null or char_length(prompt_version) <= 50),
  context_version text check (context_version is null or char_length(context_version) <= 50),
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (decision_episode_id, user_id)
    references public.decision_episodes(id, user_id) on delete cascade,
  unique (decision_episode_id, version),
  unique (id, user_id),
  check (status not in ('accepted', 'rejected') or reviewed_at is not null)
);

create table public.action_plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  decision_episode_id uuid not null,
  source_report_draft_id uuid,
  schema_version text not null default '2.0' check (schema_version = '2.0'),
  status public.v2_action_plan_status not null default 'draft',
  objective text not null check (char_length(objective) between 1 and 3000),
  success_criteria text check (success_criteria is null or char_length(success_criteria) <= 2000),
  key_assumptions jsonb not null default '[]'::jsonb
    check (jsonb_typeof(key_assumptions) = 'array'),
  major_obstacles jsonb not null default '[]'::jsonb
    check (jsonb_typeof(major_obstacles) = 'array'),
  fallback_plan text check (fallback_plan is null or char_length(fallback_plan) <= 2000),
  review_at timestamptz,
  confirmed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (decision_episode_id, user_id)
    references public.decision_episodes(id, user_id) on delete cascade,
  foreign key (source_report_draft_id, user_id)
    references public.decision_report_drafts(id, user_id),
  unique (id, user_id),
  check (status not in ('confirmed', 'in_progress', 'completed') or confirmed_at is not null)
);

create table public.action_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  action_plan_id uuid not null,
  schema_version text not null default '2.0' check (schema_version = '2.0'),
  description text not null check (char_length(description) between 1 and 2000),
  sequence integer not null check (sequence > 0),
  due_at timestamptz,
  status public.v2_action_item_status not null default 'pending',
  completion_note text check (
    completion_note is null or char_length(completion_note) <= 2000
  ),
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (action_plan_id, user_id)
    references public.action_plans(id, user_id) on delete cascade,
  unique (action_plan_id, sequence),
  unique (id, user_id),
  check (status <> 'completed' or completed_at is not null)
);

create table public.feedback_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  decision_episode_id uuid not null,
  action_plan_id uuid,
  corrects_feedback_id uuid,
  schema_version text not null default '2.0' check (schema_version = '2.0'),
  feedback_type public.v2_feedback_type not null,
  status public.v2_feedback_status not null default 'draft',
  actual_actions jsonb not null default '[]'::jsonb
    check (jsonb_typeof(actual_actions) = 'array'),
  actual_outcome text check (actual_outcome is null or char_length(actual_outcome) <= 5000),
  expected_vs_actual text check (
    expected_vs_actual is null or char_length(expected_vs_actual) <= 5000
  ),
  assumptions_validated jsonb not null default '[]'::jsonb
    check (jsonb_typeof(assumptions_validated) = 'array'),
  assumptions_invalidated jsonb not null default '[]'::jsonb
    check (jsonb_typeof(assumptions_invalidated) = 'array'),
  external_factors jsonb not null default '[]'::jsonb
    check (jsonb_typeof(external_factors) = 'array'),
  user_reflection text check (user_reflection is null or char_length(user_reflection) <= 5000),
  lessons_learned jsonb not null default '[]'::jsonb
    check (jsonb_typeof(lessons_learned) = 'array'),
  future_adjustments jsonb not null default '[]'::jsonb
    check (jsonb_typeof(future_adjustments) = 'array'),
  occurred_at timestamptz,
  confirmed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (decision_episode_id, user_id)
    references public.decision_episodes(id, user_id) on delete cascade,
  foreign key (action_plan_id, user_id)
    references public.action_plans(id, user_id),
  foreign key (corrects_feedback_id, user_id)
    references public.feedback_entries(id, user_id),
  unique (id, user_id),
  check (status not in ('confirmed', 'corrected') or confirmed_at is not null)
);

create table public.memory_candidates (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  decision_episode_id uuid not null,
  feedback_id uuid,
  schema_version text not null default '2.0' check (schema_version = '2.0'),
  candidate_type public.v2_memory_type not null,
  proposed_content text not null check (char_length(proposed_content) between 1 and 5000),
  rationale text not null check (char_length(rationale) between 1 and 2000),
  evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(evidence) = 'array'),
  applicable_domains jsonb not null default '[]'::jsonb
    check (jsonb_typeof(applicable_domains) = 'array'),
  confidence numeric(4,3) not null default 0 check (confidence between 0 and 1),
  status public.v2_memory_candidate_status not null default 'suggested',
  proposed_expires_at timestamptz,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (decision_episode_id, user_id)
    references public.decision_episodes(id, user_id) on delete cascade,
  foreign key (feedback_id, user_id)
    references public.feedback_entries(id, user_id),
  unique (id, user_id),
  check (status not in ('confirmed', 'rejected') or reviewed_at is not null)
);

create table public.decision_memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  source_candidate_id uuid not null,
  supersedes_memory_id uuid,
  schema_version text not null default '2.0' check (schema_version = '2.0'),
  memory_type public.v2_memory_type not null,
  content text not null check (char_length(content) between 1 and 5000),
  applicable_domains jsonb not null default '[]'::jsonb
    check (jsonb_typeof(applicable_domains) = 'array'),
  evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(evidence) = 'array'),
  confidence numeric(4,3) not null default 0 check (confidence between 0 and 1),
  status public.v2_decision_memory_status not null default 'active',
  effective_from timestamptz,
  effective_until timestamptz,
  review_after timestamptz,
  confirmed_at timestamptz not null,
  last_used_at timestamptz,
  usage_count integer not null default 0 check (usage_count >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (source_candidate_id, user_id)
    references public.memory_candidates(id, user_id) on delete restrict,
  foreign key (supersedes_memory_id, user_id)
    references public.decision_memories(id, user_id),
  unique (source_candidate_id),
  unique (id, user_id),
  check (effective_until is null or effective_from is null or effective_until > effective_from)
);

-- Query paths used by profile loading, timelines, report versions, actions,
-- feedback, and memory retrieval.
create index decision_profile_versions_user_status_idx
  on public.decision_profile_versions (user_id, status, version desc);
create index decision_episodes_user_created_idx
  on public.decision_episodes (user_id, created_at desc, id desc);
create index decision_episodes_user_status_idx
  on public.decision_episodes (user_id, status, updated_at desc);
create index decision_episodes_user_domain_idx
  on public.decision_episodes (user_id, domain) where domain is not null;
create index decision_report_drafts_episode_version_idx
  on public.decision_report_drafts (decision_episode_id, version desc);
create index action_plans_episode_status_idx
  on public.action_plans (decision_episode_id, status, updated_at desc);
create index action_items_plan_sequence_idx
  on public.action_items (action_plan_id, sequence);
create index feedback_entries_episode_created_idx
  on public.feedback_entries (decision_episode_id, created_at desc);
create index feedback_entries_user_status_idx
  on public.feedback_entries (user_id, status, updated_at desc);
create index memory_candidates_user_status_idx
  on public.memory_candidates (user_id, status, created_at desc);
create index decision_memories_user_status_idx
  on public.decision_memories (user_id, status, updated_at desc);
create index decision_memories_user_review_idx
  on public.decision_memories (user_id, review_after)
  where status in ('active', 'needs_review');

-- Reuse the foundation migration's security-invoker timestamp function.
create trigger personal_decision_profiles_set_updated_at
before update on public.personal_decision_profiles
for each row execute function public.set_updated_at();
create trigger decision_profile_versions_set_updated_at
before update on public.decision_profile_versions
for each row execute function public.set_updated_at();
create trigger decision_episodes_set_updated_at
before update on public.decision_episodes
for each row execute function public.set_updated_at();
create trigger decision_report_drafts_set_updated_at
before update on public.decision_report_drafts
for each row execute function public.set_updated_at();
create trigger action_plans_set_updated_at
before update on public.action_plans
for each row execute function public.set_updated_at();
create trigger action_items_set_updated_at
before update on public.action_items
for each row execute function public.set_updated_at();
create trigger feedback_entries_set_updated_at
before update on public.feedback_entries
for each row execute function public.set_updated_at();
create trigger memory_candidates_set_updated_at
before update on public.memory_candidates
for each row execute function public.set_updated_at();
create trigger decision_memories_set_updated_at
before update on public.decision_memories
for each row execute function public.set_updated_at();

alter table public.personal_decision_profiles enable row level security;
alter table public.decision_profile_versions enable row level security;
alter table public.decision_episodes enable row level security;
alter table public.decision_report_drafts enable row level security;
alter table public.action_plans enable row level security;
alter table public.action_items enable row level security;
alter table public.feedback_entries enable row level security;
alter table public.memory_candidates enable row level security;
alter table public.decision_memories enable row level security;

create policy personal_decision_profiles_own on public.personal_decision_profiles
for all to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
create policy decision_profile_versions_own on public.decision_profile_versions
for all to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
create policy decision_episodes_own on public.decision_episodes
for all to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
create policy decision_report_drafts_own on public.decision_report_drafts
for all to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
create policy action_plans_own on public.action_plans
for all to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
create policy action_items_own on public.action_items
for all to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
create policy feedback_entries_own on public.feedback_entries
for all to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
create policy memory_candidates_own on public.memory_candidates
for all to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
create policy decision_memories_own on public.decision_memories
for all to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

revoke all on public.personal_decision_profiles, public.decision_profile_versions,
  public.decision_episodes, public.decision_report_drafts, public.action_plans,
  public.action_items, public.feedback_entries, public.memory_candidates,
  public.decision_memories from anon;
grant select, insert, update, delete on public.personal_decision_profiles,
  public.decision_profile_versions, public.decision_episodes,
  public.decision_report_drafts, public.action_plans, public.action_items,
  public.feedback_entries, public.memory_candidates, public.decision_memories
  to authenticated;

-- V1 tables remain intact and writable for compatibility during migration.
-- These comments are the non-destructive Legacy marker for schema inspection.
comment on table public.reflections is
  'LEGACY V1: retained for compatibility. New decisions use public.decision_episodes.';
comment on table public.growth_scores is
  'LEGACY V1: retained read/write during migration. V2 Growth Map is non-scoring.';
comment on table public.memories is
  'LEGACY V1: retained for compatibility. New memory uses candidates plus confirmed decision memories.';

comment on table public.personal_decision_profiles is
  'Growth Atlas V2 profile aggregate; detailed immutable content lives in decision_profile_versions.';
comment on table public.decision_episodes is
  'Growth Atlas V2 aggregate root for a decision, action, feedback, and memory lifecycle.';
comment on table public.decision_report_drafts is
  'AI-generated analysis drafts; a draft is not the user final decision.';
comment on table public.memory_candidates is
  'AI/system memory proposals awaiting explicit user review.';
comment on table public.decision_memories is
  'User-confirmed long-term decision memory available to future retrieval.';
