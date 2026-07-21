-- Sprint 5: atomically preserve the reviewed AI draft and the user's final decision.

alter table public.decision_episodes
  add column confirmed_from_draft_id uuid;

alter table public.decision_episodes
  add constraint decision_episodes_confirmed_draft_fk
  foreign key (confirmed_from_draft_id, user_id)
  references public.decision_report_drafts(id, user_id);

create index decision_episodes_confirmed_draft_idx
  on public.decision_episodes (confirmed_from_draft_id)
  where confirmed_from_draft_id is not null;

create or replace function public.confirm_decision_episode(
  p_episode_id uuid,
  p_draft_id uuid,
  p_final_decision text,
  p_decision_rationale text default null
)
returns setof public.decision_episodes
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
  current_user_id uuid := auth.uid();
  episode_status public.v2_decision_episode_status;
begin
  if current_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  if p_final_decision is null or char_length(btrim(p_final_decision)) = 0 then
    raise exception 'final decision is required' using errcode = '22023';
  end if;
  if char_length(p_final_decision) > 5000
     or char_length(coalesce(p_decision_rationale, '')) > 5000 then
    raise exception 'decision content is too long' using errcode = '22023';
  end if;

  select status into episode_status
  from public.decision_episodes
  where id = p_episode_id and user_id = current_user_id
  for update;

  if episode_status is null then
    raise exception 'decision episode not found' using errcode = 'P0002';
  end if;
  if episode_status not in ('draft_ready', 'awaiting_user_decision') then
    raise exception 'decision episode cannot be confirmed from current status'
      using errcode = 'P0001';
  end if;
  if not exists (
    select 1 from public.decision_report_drafts
    where id = p_draft_id
      and decision_episode_id = p_episode_id
      and user_id = current_user_id
      and status = 'ready'
    for update
  ) then
    raise exception 'ready decision draft not found' using errcode = 'P0002';
  end if;

  update public.decision_report_drafts
  set status = 'accepted', reviewed_at = now()
  where id = p_draft_id and user_id = current_user_id;

  return query
  update public.decision_episodes
  set status = 'committed',
      final_decision = btrim(p_final_decision),
      decision_rationale = nullif(btrim(p_decision_rationale), ''),
      confirmed_from_draft_id = p_draft_id,
      committed_at = now()
  where id = p_episode_id and user_id = current_user_id
  returning *;
end;
$$;

revoke all on function public.confirm_decision_episode(uuid, uuid, text, text) from public;
grant execute on function public.confirm_decision_episode(uuid, uuid, text, text)
  to authenticated;

comment on column public.decision_episodes.confirmed_from_draft_id is
  'The immutable AI draft reviewed before the user recorded a separate final decision.';
comment on function public.confirm_decision_episode(uuid, uuid, text, text) is
  'Atomically accepts a reviewed AI draft and commits the user-owned final decision.';
