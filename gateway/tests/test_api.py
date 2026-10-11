from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def _settings(routes_path: Path, **overrides: object) -> Settings:
    values = {"routes_path": routes_path, "reload_interval_seconds": 0, **overrides}
    return Settings(**values)  # type: ignore[arg-type]


def _app(routes_path: Path) -> TestClient:
    return TestClient(create_app(_settings(routes_path)))


def _patch_upstream(monkeypatch: pytest.MonkeyPatch, handler: object) -> None:
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]

    def fake_client(_settings: Settings) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport, base_url="http://upstream")

    monkeypatch.setattr("app.main._build_client", fake_client)


def test_healthz(routes_path: Path) -> None:
    with _app(routes_path) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_list_models(routes_path: Path) -> None:
    with _app(routes_path) as client:
        response = client.get("/v1/models")
        assert response.status_code == 200
        ids = {item["id"] for item in response.json()["data"]}
        assert "llama-8b" in ids
        assert "llama-8b-vllm-fp16" in ids


def test_unknown_model_is_404(routes_path: Path) -> None:
    with _app(routes_path) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "nope", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert response.status_code == 404


def test_non_stream_proxy(routes_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "llama-8b"
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
            },
        )

    _patch_upstream(monkeypatch, handler)
    with TestClient(create_app(_settings(routes_path))) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "llama-8b-vllm-fp16", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "ok"


def test_stream_proxy_passthrough(routes_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                b'data: {"choices":[{"delta":{"content":"hel"}}]}\n\n'
                b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    _patch_upstream(monkeypatch, handler)
    with TestClient(create_app(_settings(routes_path))) as client:  # noqa: SIM117
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "llama-8b-vllm-fp16",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        ) as response:
            payload = b"".join(response.iter_bytes())
    assert b"hel" in payload
    assert b"[DONE]" in payload


def test_connect_error_retries_once(routes_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(
            200,
            json={"id": "ok", "choices": [{"message": {"role": "assistant", "content": "retry"}}]},
        )

    _patch_upstream(monkeypatch, handler)
    with TestClient(create_app(_settings(routes_path, retry_connect=True))) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "llama-8b-vllm-fp16", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert response.status_code == 200
    assert attempts["n"] == 2


def test_metrics_endpoint(routes_path: Path) -> None:
    with TestClient(create_app(_settings(routes_path))) as client:
        response = client.get("/metrics")
    assert response.status_code == 200
    assert "infergrid_gateway_requests_total" in response.text
