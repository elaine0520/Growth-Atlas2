# Supabase setup

Phase 1 is defined by these migrations, applied in filename order:

1. `migrations/202607120001_phase_1_foundation.sql`
2. `migrations/202607140001_profile_pipeline_hardening.sql`
3. `migrations/202607190001_v2_domain_foundation.sql`
4. `migrations/202607190002_decision_episode_creation.sql`
5. `migrations/202607200001_user_confirmation.sql`
6. `migrations/202607200002_action_plan_feedback.sql`
7. `migrations/202607200003_decision_memory_system.sql`
8. `migrations/202607200004_context_builder_v2.sql`

The migration creates the Growth Atlas core tables, automatically creates one
`profiles` row for every Auth user, enables RLS on every user-owned table, and
removes all anonymous table access.

The hardening migration backfills profiles for Auth users that existed before
the trigger was installed and adds an RLS-protected recovery insert for a user
whose own profile row is missing.

Apply migrations through the Supabase CLI when the project is linked, or paste
the migration into the Supabase SQL editor once. Never expose the service-role
key to the frontend.

## Growth Atlas V2 domain foundation

The V2 migration adds the Personal Decision System tables without deleting or
rewriting V1 data. It introduces versioned decision profiles, decision
episodes, reviewable AI report drafts, user-confirmed action plans and
feedback, and a two-stage memory flow (`memory_candidates` followed by
`decision_memories`).

The V1 `reflections`, `growth_scores`, and `memories` tables remain available
during the compatibility period. Database comments mark them as Legacy; the
migration does not rename, truncate, or backfill them.

Every V2 table:

- carries `user_id` and schema version `2.0`;
- uses row-level security restricted to `auth.uid()`;
- revokes anonymous access;
- uses composite foreign keys where relationships must remain within one user;
- has lifecycle, JSON shape, length, range, and confirmation constraints.

See `V2_DATABASE.md` for the table map, lifecycle rules, RLS audit queries, and
data migration risks. This Sprint creates the V2 schema only; legacy data
backfill belongs to a separate reviewed migration.
