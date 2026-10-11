import json

import httpx
import pytest

from clients.triage.assistant import classify_http, main


def test_classify_http_maps_label(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(*_a: object, **_k: object) -> httpx.Response:
        request = httpx.Request("POST", "http://gw/v1/chat/completions")
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "This is a billing issue"}}]},
        )

    monkeypatch.setattr("clients.triage.assistant.httpx.post", fake_post)
    assert classify_http("I was charged twice", base_url="http://gw", model="llama-8b") == "billing"


def test_main_prints_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "clients.triage.assistant.classify",
        lambda *_a, **_k: "bug",
    )
    main(["the app crashes on login", "--model", "mock-qwen"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["label"] == "bug"
    assert payload["model"] == "mock-qwen"
