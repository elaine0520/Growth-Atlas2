"""Tests for the mock MVP API layer."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def test_profile_rejects_url_misconfigured_as_supabase_key() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="https://api.example.com/v1/",
    )
    try:
        response = client.get(
            "/api/profile",
            headers={"Authorization": "Bearer access-token"},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "Supabase Auth is not configured correctly"


def test_profile_requires_access_token() -> None:
    response = client.get("/api/profile")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing access token"


def test_decision_episode_creation_requires_access_token() -> None:
    response = client.post(
        "/api/decision-episodes",
        json={
            "title": "是否接受实习",
            "decision_question": "我是否应该接受这个实习机会？",
        },
    )

    assert response.status_code == 401


def test_decision_review_endpoints_require_access_token() -> None:
    episode_id = uuid4()
    draft_response = client.get(f"/api/decision-episodes/{episode_id}/drafts/latest/ready")
    confirm_response = client.post(
        f"/api/decision-episodes/{episode_id}/confirm",
        json={"draft_id": str(uuid4()), "final_decision": "我的选择"},
    )

    assert draft_response.status_code == 401
    assert confirm_response.status_code == 401


def test_action_and_feedback_endpoints_require_access_token() -> None:
    episode_id = uuid4()
    plan_response = client.post(
        f"/api/decision-episodes/{episode_id}/action-plan",
        json={"objective": "执行决定", "actions": ["完成第一步"]},
    )
    feedback_response = client.post(
        f"/api/decision-episodes/{episode_id}/feedback",
        json={
            "action_plan_id": str(uuid4()),
            "actual_outcome": "完成",
            "expected_vs_actual": "符合预期",
            "lessons_learned": ["保持跟进"],
        },
    )

    assert plan_response.status_code == 401
    assert feedback_response.status_code == 401


def test_memory_management_requires_access_token() -> None:
    list_response = client.get("/api/memory")
    candidate_response = client.post(
        "/api/memory/candidates",
        json={
            "feedback_id": str(uuid4()), "candidate_type": "confirmed_lesson",
            "proposed_content": "一条经验", "rationale": "来自现实反馈",
        },
    )
    delete_response = client.delete(f"/api/memory/{uuid4()}")

    assert list_response.status_code == 401
    assert candidate_response.status_code == 401
    assert delete_response.status_code == 401


def test_growth_map_and_v2_timeline_require_access_token() -> None:
    growth_map_response = client.get("/api/growth-map")
    timeline_response = client.get("/api/decision-timeline")

    assert growth_map_response.status_code == 401
    assert timeline_response.status_code == 401


def test_profile_does_not_accept_client_supplied_user_id() -> None:
    response = client.put(
        "/api/profile",
        headers={"Authorization": "Bearer invalid"},
        json={"user_id": str(uuid4()), "user_info": {"nickname": "Atlas"}},
    )

    # Authentication is checked before payload ownership can be trusted.
    assert response.status_code in {401, 503}


def test_create_reflection() -> None:
    response = client.post(
        "/api/reflection",
        json={
            "user_id": str(uuid4()),
            "title": "如何开始重要任务",
            "user_question": "我总是推迟开始，下一步可以做什么？",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "saved"
    assert "模拟分析" in response.json()["ai_analysis"]


def test_get_report() -> None:
    response = client.get("/api/report")

    assert response.status_code == 200
    assert len(response.json()["growth_scores"]) == 6
    assert response.json()["model_name"] is None
