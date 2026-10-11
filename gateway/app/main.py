from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, Response

from app import metrics
from app.proxy import UpstreamError, proxy_chat
from app.routing import RouteStore, UnknownModelError
from app.schemas import ChatCompletionRequest, ModelCard, ModelList
from app.settings import Settings, load_settings

logger = logging.getLogger("infergrid.gateway")


class AppState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.routes = RouteStore(settings.routes_path)
        self.client: httpx.AsyncClient | None = None
        self._reloader: asyncio.Task[None] | None = None


def _build_client(settings: Settings) -> httpx.AsyncClient:
    timeout = httpx.Timeout(
        connect=settings.connect_timeout_seconds,
        read=settings.read_timeout_seconds,
        write=settings.write_timeout_seconds,
        pool=settings.pool_timeout_seconds,
    )
    limits = httpx.Limits(
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
    )
    return httpx.AsyncClient(timeout=timeout, limits=limits)


async def _reload_loop(store: RouteStore, interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            if store.reload_if_changed():
                logger.info("reloaded routes from %s", store.path)
        except Exception:
            logger.exception("route reload failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.holder.settings
    store: RouteStore = app.state.holder.routes
    if settings.routes_path.exists():
        store.load()
        logger.info("loaded %s routes from %s", len(store.table().routes), settings.routes_path)
    else:
        logger.warning(
            "routes file %s is missing; starting with an empty table", settings.routes_path
        )

    client = _build_client(settings)
    app.state.holder.client = client
    if settings.reload_interval_seconds > 0:
        app.state.holder._reloader = asyncio.create_task(
            _reload_loop(store, settings.reload_interval_seconds)
        )
    try:
        yield
    finally:
        reloader = app.state.holder._reloader
        if reloader is not None:
            reloader.cancel()
            with suppress(asyncio.CancelledError):
                await reloader
        await client.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="infergrid-gateway", version="0.1.0", lifespan=lifespan)
    app.state.holder = AppState(settings)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        table = app.state.holder.routes.table()
        client = app.state.holder.client
        if client is None or not table.routes:
            return JSONResponse({"status": "not_ready", "reason": "no_routes"}, status_code=503)

        timeout = app.state.holder.settings.ready_check_timeout_seconds
        any_ready = False
        backends: dict[str, str] = {}
        for route in table.routes.values():
            url = route.url.rstrip("/") + (
                "/v2/health/ready"
                if route.backend == "triton" and not route.openai_compatible
                else "/health"
            )
            try:
                response = await client.get(url, timeout=timeout)
                ready = response.status_code < 400
            except httpx.HTTPError:
                ready = False
            metrics.BACKEND_READY.labels(backend=route.backend, route=route.name).set(
                1 if ready else 0
            )
            backends[route.name] = "ready" if ready else "down"
            any_ready = any_ready or ready

        status = 200 if any_ready else 503
        return JSONResponse(
            {"status": "ready" if any_ready else "not_ready", "backends": backends},
            status_code=status,
        )

    @app.get("/metrics")
    async def prometheus_metrics() -> Response:
        payload, content_type = metrics.render()
        return Response(content=payload, media_type=content_type)

    @app.get("/v1/models")
    async def list_models() -> ModelList:
        table = app.state.holder.routes.table()
        cards = [
            ModelCard(id=name, backend=table.routes[name].backend)
            if name in table.routes
            else ModelCard(id=name, owned_by="infergrid-alias")
            for name in table.listed_models()
        ]
        return ModelList(data=cards)

    @app.post("/v1/chat/completions")
    async def chat_completions(
        body: ChatCompletionRequest,
        x_backend: str | None = Header(default=None, convert_underscores=True),
    ) -> Any:
        table = app.state.holder.routes.table()
        client = app.state.holder.client
        if client is None:
            raise HTTPException(status_code=503, detail="gateway not started")
        try:
            resolution = table.resolve(body.model, backend=x_backend)
        except UnknownModelError as exc:
            raise HTTPException(status_code=404, detail=f"unknown model: {exc}") from exc

        try:
            return await proxy_chat(
                client,
                resolution,
                body,
                retry_connect=app.state.holder.settings.retry_connect,
            )
        except UpstreamError as exc:
            return JSONResponse(
                {"error": {"message": exc.detail, "type": "upstream_error"}},
                status_code=exc.status_code,
            )

    return app


app = create_app()
