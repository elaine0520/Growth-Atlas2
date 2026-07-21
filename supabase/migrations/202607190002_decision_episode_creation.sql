-- Sprint 3: capture user-owned background before AI analysis begins.

alter table public.decision_episodes
  add column background text
  check (background is null or char_length(background) <= 5000);

comment on column public.decision_episodes.background is
  'User-provided background for this decision; not an AI-generated context snapshot.';
