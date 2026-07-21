import os
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.observability import configure_observability


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app() -> FastAPI:
    settings = get_settings()
    # Supabase is directly reachable in local preview. Bypass flaky desktop
    # proxies for this host while preserving proxy settings for other services.
    if settings.supabase_url:
        supabase_host = urlparse(settings.supabase_url).hostname
        if supabase_host:
            existing_no_proxy = os.environ.get("NO_PROXY", "")
            no_proxy_hosts = [host.strip() for host in existing_no_proxy.split(",") if host.strip()]
            if supabase_host not in no_proxy_hosts:
                os.environ["NO_PROXY"] = ",".join([*no_proxy_hosts, supabase_host])
    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    configure_observability(application, settings)
    application.include_router(api_router, prefix=settings.api_prefix)
    if FRONTEND_DIST.is_dir():
        application.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return application


app = create_app()
