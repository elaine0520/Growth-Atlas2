-- Sprint 8: preserve the exact retrieved context on every generated draft version.

alter table public.decision_report_drafts
  add column context_snapshot jsonb;

alter table public.decision_report_drafts
  add constraint decision_report_drafts_context_snapshot_object_check
  check (context_snapshot is null or jsonb_typeof(context_snapshot) = 'object');

comment on column public.decision_report_drafts.context_snapshot is
  'Immutable-at-generation record of confirmed Profile items, relevant valid Memory IDs, historical Episode IDs, confidence, and relevance used by AI.';
