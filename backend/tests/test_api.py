"""Tests for the mock MVP API layer."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_profile_requires_access_token() -> None:
    response = client.get("/api/profile")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing access token"


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
