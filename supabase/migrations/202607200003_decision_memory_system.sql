-- Sprint 7: explicit, evidence-backed Decision Memory confirmation.

create unique index memory_candidates_one_live_per_feedback_type_idx
  on public.memory_candidates (feedback_id, candidate_type)
  where feedback_id is not null and status in ('suggested', 'edited', 'confirmed');

create or replace function public.create_feedback_memory_candidate(
  p_feedback_id uuid,
  p_candidate_type public.v2_memory_type,
  p_proposed_content text,
  p_rationale text,
  p_applicable_domains jsonb default '[]'::jsonb
)
returns setof public.memory_candidates
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  current_user_id uuid := auth.uid();
  source_feedback public.feedback_entries;
begin
  if current_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  if nullif(btrim(p_proposed_content), '') is null
     or char_length(p_proposed_content) > 5000 then
    raise exception 'valid candidate content is required' using errcode = '22023';
  end if;
  if nullif(btrim(p_rationale), '') is null or char_length(p_rationale) > 2000 then
    raise exception 'valid rationale is required' using errcode = '22023';
  end if;
  if jsonb_typeof(p_applicable_domains) <> 'array' then
    raise exception 'applicable domains must be an array' using errcode = '22023';
  end if;

  select * into source_feedback
  from public.feedback_entries
  where id = p_feedback_id and user_id = current_user_id and status = 'confirmed';
  if not found then
    raise exception 'confirmed feedback not found' using errcode = 'P0002';
  end if;

  return query
  insert into public.memory_candidates (
    user_id, decision_episode_id, feedback_id, candidate_type,
    proposed_content, rationale, evidence, applicable_domains,
    confidence, status
  ) values (
    current_user_id, source_feedback.decision_episode_id, source_feedback.id,
    p_candidate_type, btrim(p_proposed_content), btrim(p_rationale),
    jsonb_build_array(
      jsonb_build_object(
        'source_type', 'feedback', 'source_id', source_feedback.id,
        'note', 'User-confirmed feedback'
      ),
      jsonb_build_object(
        'source_type', 'decision_episode',
        'source_id', source_feedback.decision_episode_id,
        'note', 'Source decision episode'
      )
    ),
    p_applicable_domains, 0.500, 'suggested'
  ) returning *;
end;
$$;

create or replace function public.confirm_memory_candidate(
  p_candidate_id uuid,
  p_content text,
  p_applicable_domains jsonb,
  p_user_confirmed boolean
)
returns setof public.decision_memories
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  current_user_id uuid := auth.uid();
  candidate public.memory_candidates;
begin
  if current_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  if p_user_confirmed is distinct from true then
    raise exception 'explicit user confirmation is required' using errcode = '22023';
  end if;
  if nullif(btrim(p_content), '') is null or char_length(p_content) > 5000 then
    raise exception 'valid memory content is required' using errcode = '22023';
  end if;
  if jsonb_typeof(p_applicable_domains) <> 'array' then
    raise exception 'applicable domains must be an array' using errcode = '22023';
  end if;

  select * into candidate
  from public.memory_candidates
  where id = p_candidate_id and user_id = current_user_id
    and status in ('suggested', 'edited')
  for update;
  if not found then
    raise exception 'reviewable memory candidate not found' using errcode = 'P0002';
  end if;
  if candidate.feedback_id is null
     or jsonb_typeof(candidate.evidence) <> 'array'
     or jsonb_array_length(candidate.evidence) = 0 then
    raise exception 'memory candidate requires source feedback and evidence'
      using errcode = '23514';
  end if;

  update public.memory_candidates
  set proposed_content = btrim(p_content), applicable_domains = p_applicable_domains,
      status = 'confirmed', confidence = greatest(confidence, 0.750), reviewed_at = now()
  where id = candidate.id and user_id = current_user_id;

  return query
  insert into public.decision_memories (
    user_id, source_candidate_id, memory_type, content, applicable_domains,
    evidence, confidence, status, effective_from, confirmed_at
  ) values (
    current_user_id, candidate.id, candidate.candidate_type, btrim(p_content),
    p_applicable_domains, candidate.evidence, greatest(candidate.confidence, 0.750),
    'active', now(), now()
  ) returning *;
end;
$$;

create or replace function public.reject_memory_candidate(p_candidate_id uuid)
returns setof public.memory_candidates
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  current_user_id uuid := auth.uid();
begin
  if current_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  return query
  update public.memory_candidates
  set status = 'rejected', reviewed_at = now()
  where id = p_candidate_id and user_id = current_user_id
    and status in ('suggested', 'edited')
  returning *;
  if not found then
    raise exception 'reviewable memory candidate not found' using errcode = 'P0002';
  end if;
end;
$$;

create or replace function public.set_decision_memory_status(
  p_memory_id uuid,
  p_target_status public.v2_decision_memory_status
)
returns setof public.decision_memories
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  current_user_id uuid := auth.uid();
  current_status public.v2_decision_memory_status;
begin
  if current_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  if p_target_status not in ('active', 'disabled', 'deleted') then
    raise exception 'unsupported memory status' using errcode = '22023';
  end if;
  select status into current_status
  from public.decision_memories
  where id = p_memory_id and user_id = current_user_id
  for update;
  if current_status is null then
    raise exception 'decision memory not found' using errcode = 'P0002';
  end if;
  if not (
    (current_status = 'active' and p_target_status in ('disabled', 'deleted'))
    or (current_status = 'needs_review' and p_target_status in ('active', 'disabled', 'deleted'))
    or (current_status = 'disabled' and p_target_status in ('active', 'deleted'))
    or (current_status in ('superseded', 'archived') and p_target_status = 'deleted')
  ) then
    raise exception 'invalid decision memory transition' using errcode = 'P0001';
  end if;
  return query
  update public.decision_memories set status = p_target_status
  where id = p_memory_id and user_id = current_user_id
  returning *;
end;
$$;

revoke all on function public.create_feedback_memory_candidate(uuid, public.v2_memory_type, text, text, jsonb) from public;
revoke all on function public.confirm_memory_candidate(uuid, text, jsonb, boolean) from public;
revoke all on function public.reject_memory_candidate(uuid) from public;
revoke all on function public.set_decision_memory_status(uuid, public.v2_decision_memory_status) from public;
grant execute on function public.create_feedback_memory_candidate(uuid, public.v2_memory_type, text, text, jsonb) to authenticated;
grant execute on function public.confirm_memory_candidate(uuid, text, jsonb, boolean) to authenticated;
grant execute on function public.reject_memory_candidate(uuid) to authenticated;
grant execute on function public.set_decision_memory_status(uuid, public.v2_decision_memory_status) to authenticated;

-- Reading remains RLS-protected, while every mutation must pass through the
-- explicit source/review/status functions above.
revoke insert, update, delete on public.memory_candidates from authenticated;
revoke insert, update, delete on public.decision_memories from authenticated;

comment on function public.confirm_memory_candidate(uuid, text, jsonb, boolean) is
  'The only Sprint 7 path that creates long-term memory; explicit user confirmation is mandatory.';
