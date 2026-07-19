-- Ensure Auth users created before the foundation migration also have a profile.
insert into public.profiles (id, nickname)
select users.id, nullif(users.raw_user_meta_data ->> 'nickname', '')
from auth.users as users
where not exists (
  select 1 from public.profiles where profiles.id = users.id
);

-- A signed-in user may recreate only their own missing profile row. Normal account
-- creation still uses handle_new_user(), so this is only a recovery path.
drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own on public.profiles for insert to authenticated
with check ((select auth.uid()) = id);

grant insert on public.profiles to authenticated;
