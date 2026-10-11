from __future__ import annotations

import threading
import time
from pathlib import Path

import httpx
import uvicorn
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings
from mock_app.main import app as mock_app


def _serve_mock(host: str, port: int) -> uvicorn.Server:
    config = uvicorn.Config(mock_app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            httpx.get(f"http://{host}:{port}/health", timeout=0.2)
            return server
        except httpx.HTTPError:
            time.sleep(0.05)
    raise RuntimeError("mock backend did not start")


def test_gateway_streams_from_live_mock(tmp_path: Path) -> None:
    host, port = "127.0.0.1", 18999
    server = _serve_mock(host, port)
    routes = tmp_path / "routes.yaml"
    routes.write_text(
        f"""
routes:
  - name: mock-qwen
    backend: mock
    url: http://{host}:{port}
    upstream_model: mock-qwen
    openai_compatible: true
""",
        encoding="utf-8",
    )
    settings = Settings(routes_path=routes, reload_interval_seconds=0)
    try:
        with TestClient(create_app(settings)) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "mock-qwen",
                    "messages": [{"role": "user", "content": "hello"}],
                    "max_tokens": 4,
                },
            )
            assert response.status_code == 200
            assert "hello-ack" in response.json()["choices"][0]["message"]["content"]

            with client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": "mock-qwen",
                    "messages": [{"role": "user", "content": "stream"}],
                    "stream": True,
                    "max_tokens": 3,
                },
            ) as streamed:
                text = "".join(streamed.iter_text())
            assert "[DONE]" in text
            models = client.get("/v1/models")
            assert models.status_code == 200
            assert models.json()["data"][0]["id"] == "mock-qwen"
    finally:
        server.should_exit = True
