# Supabase setup

Phase 1 is defined by these migrations, applied in filename order:

1. `migrations/202607120001_phase_1_foundation.sql`
2. `migrations/202607140001_profile_pipeline_hardening.sql`

The migration creates the Growth Atlas core tables, automatically creates one
`profiles` row for every Auth user, enables RLS on every user-owned table, and
removes all anonymous table access.

The hardening migration backfills profiles for Auth users that existed before
the trigger was installed and adds an RLS-protected recovery insert for a user
whose own profile row is missing.

Apply migrations through the Supabase CLI when the project is linked, or paste
the migration into the Supabase SQL editor once. Never expose the service-role
key to the frontend.
