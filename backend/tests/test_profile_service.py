import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from app.core.auth import CurrentUser
from app.core.config import Settings
from app.services import profile_service


def _profile_row(user_id: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": user_id,
        "status": "draft",
        "version": 1,
        "created_at": now,
        "updated_at": now,
    }


def test_missing_profile_is_initialized_for_authenticated_user(monkeypatch) -> None:
    user = CurrentUser(id=uuid4(), email="preview@example.com", access_token="user-token")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(201, json=[_profile_row(str(user.id))])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(profile_service.httpx, "AsyncClient", lambda **_: client)

    profile = asyncio.run(
        profile_service.get_profile(
            Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon-key"),
            user,
        )
    )

    assert profile.id == user.id
    assert [request.method for request in requests] == ["GET", "POST"]
    assert requests[1].headers["authorization"] == "Bearer user-token"
    assert requests[1].headers["prefer"] == "resolution=merge-duplicates,return=representation"
