import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.observability import configure_observability


def _test_app(exception: Exception) -> FastAPI:
    application = FastAPI()
    configure_observability(application, Settings(app_env="test"))

    @application.get("/fail")
    async def fail() -> None:
        raise exception

    return application


def test_unhandled_errors_are_safe_and_traceable() -> None:
    client = TestClient(_test_app(RuntimeError("database-password-must-not-leak")), raise_server_exceptions=False)

    response = client.get("/fail", headers={"X-Request-ID": "error-123"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error", "request_id": "error-123"}
    assert response.headers["X-Request-ID"] == "error-123"
    assert "database-password" not in response.text


def test_upstream_errors_are_reported_as_service_unavailable() -> None:
    request = httpx.Request("GET", "https://private-upstream.example")
    client = TestClient(
        _test_app(httpx.ConnectError("private-upstream-token", request=request)),
        raise_server_exceptions=False,
    )

    response = client.get("/fail")

    assert response.status_code == 503
    assert response.json()["detail"] == "Upstream service unavailable"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert "private-upstream" not in response.text
