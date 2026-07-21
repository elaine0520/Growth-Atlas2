from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_missing_dependencies_without_exposing_secrets() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        kimi_api_key=None,
        supabase_url=None,
        supabase_anon_key=None,
    )
    try:
        response = client.get("/api/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "environment": "test",
        "dependencies": {"ai": False, "supabase": False},
        "configuration_issues": [],
    }


def test_readiness_reports_configured_dependencies() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        kimi_api_key="secret-value",
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-value",
    )
    try:
        response = client.get("/api/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["configuration_issues"] == []
    assert "secret-value" not in response.text


def test_request_id_is_preserved() -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "beta-check-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "beta-check-123"


def test_readiness_rejects_unsafe_production_configuration() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="production",
        debug=True,
        kimi_api_key="secret-value",
        supabase_url="http://example.supabase.co",
        supabase_anon_key="anon-value",
        cors_allowed_origins="http://localhost:5173",
    )
    try:
        response = client.get("/api/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["configuration_issues"]
    assert "secret-value" not in response.text
