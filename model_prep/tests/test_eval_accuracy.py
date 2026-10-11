import httpx
import pytest

from model_prep.eval_accuracy import extract_number, harness_command, run_smoke, score_item


def test_extract_and_score() -> None:
    assert extract_number("The answer is 42.") == "42"
    assert score_item("4", "4", numeric=True)
    assert score_item("I think CO2 is right", "CO2", numeric=False)


def test_harness_command_lists_gsm8k_and_mmlu() -> None:
    cmd = harness_command("http://gw", "llama-8b", 250)
    assert "gsm8k,mmlu" in cmd
    assert "250" in cmd


def test_run_smoke_against_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        prompt = request.read().decode()
        answer = "4" if "2 + 2" in prompt else "7" if "10 - 3" in prompt else "ok"
        if "5 * 6" in prompt:
            answer = "30"
        if "week" in prompt:
            answer = "7"
        if "exhale" in prompt:
            answer = "CO2"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": answer}}]},
        )

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def fake_client(*_a: object, **_k: object) -> httpx.Client:
        return real_client(transport=transport)

    monkeypatch.setattr("model_prep.eval_accuracy.httpx.Client", fake_client)
    scores = run_smoke("http://gw", "mock-qwen")
    assert scores["gsm8k_smoke"]["acc"] == 1.0
    assert scores["mmlu_smoke"]["acc"] == 1.0
