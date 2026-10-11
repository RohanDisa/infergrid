from __future__ import annotations

import time
from collections.abc import AsyncIterator

import httpx
from fastapi.responses import JSONResponse, StreamingResponse

from app import metrics
from app.adapters import upstream_payload, upstream_url
from app.routing import ConcreteRoute, RouteResolution
from app.schemas import ChatCompletionRequest

RETRYABLE = (httpx.ConnectError, httpx.ConnectTimeout)


class UpstreamError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def _send_once(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, object],
    *,
    stream: bool,
    headers: dict[str, str],
) -> httpx.Response:
    request = client.build_request("POST", url, json=payload, headers=headers)
    return await client.send(request, stream=stream)


async def _send_with_connect_retry(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, object],
    *,
    stream: bool,
    headers: dict[str, str],
    retry: bool,
) -> httpx.Response:
    try:
        return await _send_once(client, url, payload, stream=stream, headers=headers)
    except RETRYABLE:
        if not retry:
            raise
        return await _send_once(client, url, payload, stream=stream, headers=headers)


async def proxy_chat(
    client: httpx.AsyncClient,
    resolution: RouteResolution,
    body: ChatCompletionRequest,
    *,
    retry_connect: bool,
) -> StreamingResponse | JSONResponse:
    route = resolution.route
    url = upstream_url(route, body)
    payload = upstream_payload(route, body)
    headers = {"accept": "text/event-stream" if body.stream else "application/json"}
    started = time.perf_counter()
    metrics.INFLIGHT.labels(backend=route.backend).inc()

    try:
        response = await _send_with_connect_retry(
            client,
            url,
            payload,
            stream=body.stream,
            headers=headers,
            retry=retry_connect,
        )
    except RETRYABLE as exc:
        metrics.ERRORS.labels(
            backend=route.backend, model=resolution.requested_model, reason="connect"
        ).inc()
        metrics.REQUESTS.labels(
            backend=route.backend, model=resolution.requested_model, status="502"
        ).inc()
        raise UpstreamError(502, f"upstream connect failed: {exc}") from exc
    except httpx.TimeoutException as exc:
        metrics.ERRORS.labels(
            backend=route.backend, model=resolution.requested_model, reason="timeout"
        ).inc()
        metrics.REQUESTS.labels(
            backend=route.backend, model=resolution.requested_model, status="504"
        ).inc()
        raise UpstreamError(504, f"upstream timeout: {exc}") from exc

    if body.stream:
        return _stream_response(response, route, resolution, started)
    return await _json_response(response, route, resolution, started)


async def _json_response(
    response: httpx.Response,
    route: ConcreteRoute,
    resolution: RouteResolution,
    started: float,
) -> JSONResponse:
    try:
        metrics.OVERHEAD.labels(backend=route.backend).observe(time.perf_counter() - started)
        content = response.content
        status = response.status_code
        metrics.REQUESTS.labels(
            backend=route.backend, model=resolution.requested_model, status=str(status)
        ).inc()
        if status >= 400:
            metrics.ERRORS.labels(
                backend=route.backend, model=resolution.requested_model, reason="upstream"
            ).inc()
        metrics.DURATION.labels(backend=route.backend, model=resolution.requested_model).observe(
            time.perf_counter() - started
        )
        return JSONResponse(content=response.json() if content else {}, status_code=status)
    finally:
        await response.aclose()
        metrics.INFLIGHT.labels(backend=route.backend).dec()


def _stream_response(
    response: httpx.Response,
    route: ConcreteRoute,
    resolution: RouteResolution,
    started: float,
) -> StreamingResponse:
    first_byte = True

    async def chunks() -> AsyncIterator[bytes]:
        nonlocal first_byte
        try:
            async for chunk in response.aiter_bytes():
                if first_byte:
                    metrics.OVERHEAD.labels(backend=route.backend).observe(
                        time.perf_counter() - started
                    )
                    first_byte = False
                yield chunk
            metrics.REQUESTS.labels(
                backend=route.backend,
                model=resolution.requested_model,
                status=str(response.status_code),
            ).inc()
            if response.status_code >= 400:
                metrics.ERRORS.labels(
                    backend=route.backend, model=resolution.requested_model, reason="upstream"
                ).inc()
        except httpx.HTTPError:
            metrics.ERRORS.labels(
                backend=route.backend, model=resolution.requested_model, reason="stream"
            ).inc()
            metrics.REQUESTS.labels(
                backend=route.backend, model=resolution.requested_model, status="502"
            ).inc()
            raise
        finally:
            await response.aclose()
            metrics.INFLIGHT.labels(backend=route.backend).dec()
            metrics.DURATION.labels(
                backend=route.backend, model=resolution.requested_model
            ).observe(time.perf_counter() - started)

    media = response.headers.get("content-type", "text/event-stream")
    return StreamingResponse(
        chunks(),
        status_code=response.status_code,
        media_type=media,
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )
