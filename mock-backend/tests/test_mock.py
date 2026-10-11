from fastapi.testclient import TestClient

from mock_app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/v2/health/ready").status_code == 200


def test_non_stream_completion() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "mock-qwen",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 4,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert "ping-ack" in body["choices"][0]["message"]["content"]
    assert body["usage"]["completion_tokens"] == 4


def test_stream_completion() -> None:
    with TestClient(app) as client:  # noqa: SIM117
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "mock-qwen",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
                "max_tokens": 3,
            },
        ) as response:
            text = "".join(response.iter_text())
    assert "data: " in text
    assert "[DONE]" in text


def test_metrics_use_vllm_names() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/chat/completions",
            json={
                "model": "mock-qwen",
                "messages": [{"role": "user", "content": "x"}],
                "max_tokens": 2,
            },
        )
        metrics = client.get("/metrics").text
    assert "vllm:num_requests_waiting" in metrics or "vllm_num_requests_waiting" in metrics
    assert "generation_tokens_total" in metrics


def test_triton_generate() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v2/models/ensemble/generate",
            json={"text_input": "hello", "max_tokens": 2},
        )
    assert response.status_code == 200
    assert "text_output" in response.json()
