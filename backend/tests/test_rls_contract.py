from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FOUNDATION = ROOT / "supabase" / "migrations" / "202607190001_v2_domain_foundation.sql"
MEMORY = ROOT / "supabase" / "migrations" / "202607200003_decision_memory_system.sql"
V2_TABLES = (
    "personal_decision_profiles",
    "decision_profile_versions",
    "decision_episodes",
    "decision_report_drafts",
    "action_plans",
    "action_items",
    "feedback_entries",
    "memory_candidates",
    "decision_memories",
)


def test_every_v2_table_enables_rls_and_has_an_owner_policy() -> None:
    sql = FOUNDATION.read_text(encoding="utf-8").lower()

    for table in V2_TABLES:
        assert f"alter table public.{table} enable row level security;" in sql
        assert f"create policy {table}_own on public.{table}" in sql
    assert sql.count("(select auth.uid()) = user_id") >= len(V2_TABLES) * 2


def test_v2_tables_are_not_available_to_anonymous_users() -> None:
    sql = FOUNDATION.read_text(encoding="utf-8").lower()

    revoke_start = sql.index("revoke all on public.personal_decision_profiles")
    revoke_end = sql.index("from anon;", revoke_start)
    revoke_block = sql[revoke_start:revoke_end]
    for table in V2_TABLES:
        assert table in revoke_block


def test_memory_writes_require_guarded_functions() -> None:
    sql = MEMORY.read_text(encoding="utf-8").lower()

    assert "revoke insert, update, delete on public.memory_candidates from authenticated;" in sql
    assert "revoke insert, update, delete on public.decision_memories from authenticated;" in sql
    for function_name in (
        "create_feedback_memory_candidate",
        "confirm_memory_candidate",
        "reject_memory_candidate",
        "set_decision_memory_status",
    ):
        assert f"function public.{function_name}" in sql
    assert sql.count("security definer") >= 4
    assert sql.count("auth.uid()") >= 4
