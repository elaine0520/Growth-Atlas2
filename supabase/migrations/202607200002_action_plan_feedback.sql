-- Sprint 6: transactional action execution and feedback. No memory is generated.

create unique index action_plans_one_active_per_episode_idx
  on public.action_plans (decision_episode_id)
  where status in ('draft', 'confirmed', 'in_progress');

create or replace function public.create_episode_action_plan(
  p_episode_id uuid,
  p_objective text,
  p_actions jsonb,
  p_success_criteria text default null,
  p_major_obstacles jsonb default '[]'::jsonb
)
returns setof public.action_plans
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
  current_user_id uuid := auth.uid();
  new_plan public.action_plans;
  action_text text;
  action_sequence integer := 0;
begin
  if current_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  if nullif(btrim(p_objective), '') is null or char_length(p_objective) > 3000 then
    raise exception 'valid objective is required' using errcode = '22023';
  end if;
  if jsonb_typeof(p_actions) <> 'array' or jsonb_array_length(p_actions) = 0 then
    raise exception 'at least one action is required' using errcode = '22023';
  end if;
  if jsonb_typeof(p_major_obstacles) <> 'array' then
    raise exception 'major obstacles must be an array' using errcode = '22023';
  end if;

  perform 1 from public.decision_episodes
  where id = p_episode_id and user_id = current_user_id and status = 'committed'
  for update;
  if not found then
    raise exception 'committed decision episode not found' using errcode = 'P0002';
  end if;

  insert into public.action_plans (
    user_id, decision_episode_id, source_report_draft_id, status, objective,
    success_criteria, major_obstacles, confirmed_at
  )
  select current_user_id, p_episode_id, confirmed_from_draft_id, 'in_progress',
    btrim(p_objective), nullif(btrim(p_success_criteria), ''), p_major_obstacles, now()
  from public.decision_episodes
  where id = p_episode_id and user_id = current_user_id
  returning * into new_plan;

  for action_text in select jsonb_array_elements_text(p_actions)
  loop
    action_sequence := action_sequence + 1;
    if nullif(btrim(action_text), '') is null or char_length(action_text) > 2000 then
      raise exception 'each action must contain 1 to 2000 characters' using errcode = '22023';
    end if;
    insert into public.action_items (
      user_id, action_plan_id, description, sequence, status
    ) values (
      current_user_id, new_plan.id, btrim(action_text), action_sequence, 'pending'
    );
  end loop;

  update public.decision_episodes set status = 'acting'
  where id = p_episode_id and user_id = current_user_id;
  return next new_plan;
end;
$$;

create or replace function public.complete_action_item(
  p_episode_id uuid,
  p_action_plan_id uuid,
  p_action_item_id uuid,
  p_completed boolean,
  p_completion_note text default null
)
returns setof public.action_items
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
  current_user_id uuid := auth.uid();
begin
  if current_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  if char_length(coalesce(p_completion_note, '')) > 2000 then
    raise exception 'completion note is too long' using errcode = '22023';
  end if;
  if not exists (
    select 1 from public.action_plans
    where id = p_action_plan_id and decision_episode_id = p_episode_id
      and user_id = current_user_id and status in ('confirmed', 'in_progress')
  ) then
    raise exception 'active action plan not found' using errcode = 'P0002';
  end if;

  return query
  update public.action_items
  set status = case when p_completed then 'completed'::public.v2_action_item_status
                    else 'pending'::public.v2_action_item_status end,
      completion_note = nullif(btrim(p_completion_note), ''),
      completed_at = case when p_completed then now() else null end
  where id = p_action_item_id and action_plan_id = p_action_plan_id
    and user_id = current_user_id
  returning *;
  if not found then
    raise exception 'action item not found' using errcode = 'P0002';
  end if;

  if not exists (
    select 1 from public.action_items
    where action_plan_id = p_action_plan_id and user_id = current_user_id
      and status <> 'completed'
  ) then
    update public.decision_episodes set status = 'awaiting_feedback'
    where id = p_episode_id and user_id = current_user_id and status = 'acting';
  elsif exists (
    select 1 from public.decision_episodes
    where id = p_episode_id and user_id = current_user_id and status = 'awaiting_feedback'
  ) then
    update public.decision_episodes set status = 'acting'
    where id = p_episode_id and user_id = current_user_id;
  end if;
end;
$$;

create or replace function public.submit_episode_feedback(
  p_episode_id uuid,
  p_action_plan_id uuid,
  p_actual_actions jsonb,
  p_actual_outcome text,
  p_expected_vs_actual text,
  p_lessons_learned jsonb
)
returns setof public.feedback_entries
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
  current_user_id uuid := auth.uid();
begin
  if current_user_id is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;
  if nullif(btrim(p_actual_outcome), '') is null
     or nullif(btrim(p_expected_vs_actual), '') is null then
    raise exception 'outcome and expected comparison are required' using errcode = '22023';
  end if;
  if char_length(p_actual_outcome) > 5000 or char_length(p_expected_vs_actual) > 5000 then
    raise exception 'feedback content is too long' using errcode = '22023';
  end if;
  if jsonb_typeof(p_actual_actions) <> 'array'
     or jsonb_typeof(p_lessons_learned) <> 'array'
     or jsonb_array_length(p_lessons_learned) = 0 then
    raise exception 'actions and lessons must be arrays with at least one lesson'
      using errcode = '22023';
  end if;

  perform 1 from public.action_plans
  where id = p_action_plan_id and decision_episode_id = p_episode_id
    and user_id = current_user_id and status in ('confirmed', 'in_progress')
  for update;
  if not found then
    raise exception 'active action plan not found' using errcode = 'P0002';
  end if;
  perform 1 from public.decision_episodes
  where id = p_episode_id and user_id = current_user_id
    and status in ('acting', 'awaiting_feedback')
  for update;
  if not found then
    raise exception 'decision episode is not accepting feedback' using errcode = 'P0001';
  end if;

  update public.action_plans set status = 'completed'
  where id = p_action_plan_id and user_id = current_user_id;

  update public.decision_episodes set status = 'reflected', closed_at = now()
  where id = p_episode_id and user_id = current_user_id;

  return query
  insert into public.feedback_entries (
    user_id, decision_episode_id, action_plan_id, feedback_type, status,
    actual_actions, actual_outcome, expected_vs_actual, lessons_learned,
    occurred_at, confirmed_at
  ) values (
    current_user_id, p_episode_id, p_action_plan_id, 'final_review', 'confirmed',
    p_actual_actions, btrim(p_actual_outcome), btrim(p_expected_vs_actual),
    p_lessons_learned, now(), now()
  ) returning *;
end;
$$;

revoke all on function public.create_episode_action_plan(uuid, text, jsonb, text, jsonb) from public;
revoke all on function public.complete_action_item(uuid, uuid, uuid, boolean, text) from public;
revoke all on function public.submit_episode_feedback(uuid, uuid, jsonb, text, text, jsonb) from public;
grant execute on function public.create_episode_action_plan(uuid, text, jsonb, text, jsonb) to authenticated;
grant execute on function public.complete_action_item(uuid, uuid, uuid, boolean, text) to authenticated;
grant execute on function public.submit_episode_feedback(uuid, uuid, jsonb, text, text, jsonb) to authenticated;

comment on function public.submit_episode_feedback(uuid, uuid, jsonb, text, text, jsonb) is
  'Closes execution with confirmed feedback. It deliberately creates no memory candidate or memory.';
