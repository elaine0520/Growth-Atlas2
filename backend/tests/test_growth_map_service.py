from datetime import datetime, timezone
from uuid import UUID

from app.services.growth_map_service import assemble_growth_map


EPISODE_ID = UUID("11111111-1111-1111-1111-111111111111")
PLAN_ID = UUID("22222222-2222-2222-2222-222222222222")
ITEM_ID = UUID("33333333-3333-3333-3333-333333333333")
FEEDBACK_ID = UUID("44444444-4444-4444-4444-444444444444")
CANDIDATE_ID = UUID("55555555-5555-5555-5555-555555555555")
MEMORY_ID = UUID("66666666-6666-6666-6666-666666666666")
NOW = datetime.now(timezone.utc).isoformat()


def test_growth_map_assembles_decision_action_feedback_and_memory_lifecycle() -> None:
    growth_map = assemble_growth_map(
        episodes=[{
            "id": str(EPISODE_ID), "title": "是否接受新工作",
            "decision_question": "是否接受需要搬家的新工作？", "domain": "career",
            "status": "reflected", "final_decision": "先协商远程入职",
            "decision_rationale": "兼顾成长与家庭", "created_at": NOW,
            "committed_at": NOW, "closed_at": NOW,
        }],
        plans=[{
            "id": str(PLAN_ID), "decision_episode_id": str(EPISODE_ID),
            "objective": "完成远程安排协商", "status": "completed",
            "success_criteria": "获得书面确认", "confirmed_at": NOW,
        }],
        action_items=[{
            "id": str(ITEM_ID), "action_plan_id": str(PLAN_ID),
            "description": "联系招聘经理", "status": "completed", "completed_at": NOW,
        }],
        feedback=[{
            "id": str(FEEDBACK_ID), "decision_episode_id": str(EPISODE_ID),
            "actual_outcome": "获得三个月远程安排", "expected_vs_actual": "符合预期",
            "lessons_learned": ["提前说明约束"], "confirmed_at": NOW,
        }],
        candidates=[{
            "id": str(CANDIDATE_ID), "decision_episode_id": str(EPISODE_ID),
        }],
        memories=[{
            "id": str(MEMORY_ID), "source_candidate_id": str(CANDIDATE_ID),
            "memory_type": "confirmed_lesson", "content": "提前说明约束有助于谈判",
            "status": "active", "applicable_domains": ["career"], "confirmed_at": NOW,
        }],
    )

    entry = growth_map.timeline[0]
    assert entry.final_decision == "先协商远程入职"
    assert entry.action_plan and entry.action_plan.actions[0].status.value == "completed"
    assert entry.feedback[0].actual_outcome == "获得三个月远程安排"
    assert entry.confirmed_experiences[0].id == MEMORY_ID
    assert growth_map.confirmed_experiences[0].source_episode_id == EPISODE_ID


def test_growth_map_contract_has_no_scores_personality_or_predictions() -> None:
    growth_map = assemble_growth_map(
        episodes=[], plans=[], action_items=[], feedback=[], candidates=[], memories=[],
    )
    serialized = growth_map.model_dump_json()

    assert "score" not in serialized.lower()
    assert "personality" not in serialized.lower()
    assert "prediction" not in serialized.lower()
