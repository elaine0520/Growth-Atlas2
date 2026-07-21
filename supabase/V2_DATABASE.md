# Growth Atlas V2 Database

## Scope

Migration `202607190001_v2_domain_foundation.sql` establishes the V2 database
foundation. It creates new structures alongside V1 and performs no legacy data
backfill.

## Table map

| Table | Purpose | Primary relationships |
| --- | --- | --- |
| `personal_decision_profiles` | One current profile aggregate per user | Auth user |
| `decision_profile_versions` | Immutable/versioned profile content | Profile, prior version |
| `decision_episodes` | Aggregate root for one decision lifecycle | Profile version |
| `decision_report_drafts` | Versioned, reviewable AI analysis | Decision episode |
| `action_plans` | User-confirmable execution plan | Episode, optional report draft |
| `action_items` | Ordered actions and completion state | Action plan |
| `feedback_entries` | Checkpoints, outcomes, and reflections | Episode, optional action plan |
| `memory_candidates` | Proposed memory awaiting user review | Episode, optional feedback |
| `decision_memories` | Explicitly confirmed long-term memory | Memory candidate, prior memory |

Sprint 3 adds `decision_episodes.background` as user-provided context captured
before AI analysis. It is deliberately separate from `context_snapshot`, which
will later record the exact profile and memory context selected for a model
request.

Sprint 5 links a committed episode to the exact reviewed AI draft through
`confirmed_from_draft_id`, while keeping `final_decision` as separate user-owned
content. Sprint 6 adds transactional functions for creating an action plan,
completing action items, and submitting confirmed feedback. The Sprint 6
feedback transaction deliberately does not insert into `memory_candidates` or
`decision_memories`.

Sprint 7 introduces the only supported long-term memory creation path. A
candidate must reference confirmed feedback and receives server-generated
Feedback and Decision Episode evidence. `confirm_memory_candidate` requires an
explicit user-confirmation flag and atomically confirms the candidate and
creates its Decision Memory. Disabled and soft-deleted memories are excluded
from active retrieval; no AI service has direct insert access through the API.

Sprint 8 stores the exact V2 retrieval snapshot on both the current Decision
Episode and its generated report-draft version. The snapshot identifies the
confirmed Profile version, selected effective Memory IDs with confidence and
relevance, selected historical Episode IDs, and retrieval/builder versions.

## Ownership and foreign keys

Every V2 resource stores `user_id`. Parent/child relationships use composite
foreign keys such as:

```text
(decision_episode_id, user_id)
    -> decision_episodes(id, user_id)
```

This prevents a valid resource ID from being linked to a different user's row,
even if application validation is bypassed. User deletion cascades from
`auth.users`; required aggregate relationships cascade or restrict. Optional
history relationships use the default `NO ACTION`, so referenced history
cannot be silently detached by an arbitrary parent deletion.

## Lifecycle enforcement

PostgreSQL enums restrict stored states. Check constraints additionally enforce
important confirmation boundaries:

- confirmed profile versions require `confirmed_at`;
- committed or later decision episodes require `committed_at` and a non-null
  `final_decision`;
- accepted/rejected report drafts require `reviewed_at`;
- confirmed/in-progress/completed action plans require `confirmed_at`;
- completed action items require `completed_at`;
- confirmed/corrected feedback requires `confirmed_at`;
- confirmed/rejected memory candidates require `reviewed_at`;
- decision memories always require `confirmed_at`.

Legal state-to-state transitions remain a backend domain responsibility; the
database prevents invalid values and missing confirmation evidence, while the
Sprint 1 state maps define which transitions are allowed.

## Row-level security

RLS is enabled on all nine V2 tables. Each table has an authenticated-user
policy with both:

```sql
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id)
```

Anonymous privileges are explicitly revoked. Authenticated users receive CRUD
privileges, with RLS continuing to restrict rows.

After applying the migration, verify coverage in Supabase with:

```sql
select relname, relrowsecurity
from pg_class
where relnamespace = 'public'::regnamespace
  and relname in (
    'personal_decision_profiles', 'decision_profile_versions',
    'decision_episodes', 'decision_report_drafts', 'action_plans',
    'action_items', 'feedback_entries', 'memory_candidates',
    'decision_memories'
  )
order by relname;
```

Expected: nine rows with `relrowsecurity = true`.

Policy inspection:

```sql
select tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename in (
    'personal_decision_profiles', 'decision_profile_versions',
    'decision_episodes', 'decision_report_drafts', 'action_plans',
    'action_items', 'feedback_entries', 'memory_candidates',
    'decision_memories'
  )
order by tablename, policyname;
```

Expected: one ownership policy per table, scoped to `authenticated`, with both
read and write ownership expressions.

## Legacy tables

The following tables are retained and marked with PostgreSQL comments:

- `reflections`: V1 question/report carrier;
- `growth_scores`: V1 scoring model, incompatible with the non-scoring V2
  Growth Map;
- `memories`: V1 unseparated memory model.

They are not deleted, renamed, truncated, or backfilled by this migration.
Existing V1 application behavior therefore remains available during the
compatibility window.

## Data migration risks

1. A V1 reflection and report do not prove that the user made or confirmed a
   final decision. They must initially migrate as an episode/report draft, not
   as a committed episode.
2. V1 profile `self_description` is user self-report, not an evidence-backed
   Decision Style observation.
3. V1 memories without explicit confirmation evidence must become memory
   candidates or `needs_review`, never active decision memories.
4. Growth scores must remain legacy evidence; they cannot be converted into V2
   Growth Map conclusions.
5. A backfill must be idempotent and keep a legacy-to-V2 ID mapping to prevent
   duplicate episodes on rerun.
6. V1 report/action writes are not transactional. Orphaned reflections or
   reports must be detected before backfill.
7. Optional history links intentionally block arbitrary parent deletion. The
   product deletion workflow will need an explicit ordered archive/delete
   operation for a complete aggregate.
8. This migration depends on `public.set_updated_at()` from the Phase 1
   foundation migration and must be applied after it.

## Sprint boundary

This database Sprint does not:

- backfill legacy rows;
- switch API reads or writes to V2;
- change frontend behavior;
- modify AI prompts;
- generate Growth Map data.
