from app.adapters import messages_to_prompt, openai_payload, triton_generate_payload, upstream_url
from app.routing import ConcreteRoute
from app.schemas import ChatCompletionRequest, ChatMessage


def test_messages_to_prompt_appends_assistant() -> None:
    prompt = messages_to_prompt(
        [ChatMessage(role="system", content="be brief"), ChatMessage(role="user", content="hi")]
    )
    assert prompt.endswith("assistant:")
    assert "user: hi" in prompt


def test_openai_payload_rewrites_upstream_model() -> None:
    route = ConcreteRoute(
        name="llama-8b-vllm-fp16",
        backend="vllm",
        url="http://vllm:8000",
        upstream_model="llama-8b",
    )
    body = ChatCompletionRequest(
        model="llama-8b-vllm-fp16",
        messages=[ChatMessage(role="user", content="hi")],
    )
    payload = openai_payload(body, route)
    assert payload["model"] == "llama-8b"


def test_triton_generate_payload_and_url() -> None:
    route = ConcreteRoute(
        name="legacy",
        backend="triton",
        url="http://triton:8000",
        upstream_model="ensemble",
        openai_compatible=False,
    )
    body = ChatCompletionRequest(
        model="llama-8b-trtllm-legacy",
        messages=[ChatMessage(role="user", content="hi")],
        stream=True,
        max_tokens=32,
    )
    payload = triton_generate_payload(body, route)
    assert payload["max_tokens"] == 32
    assert payload["stream"] is True
    assert "user: hi" in payload["text_input"]
    assert upstream_url(route, body).endswith("/v2/models/ensemble/generate_stream")
