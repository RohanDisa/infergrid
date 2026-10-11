"""Upstream request adapters.

vLLM and recent Triton images speak OpenAI chat completions natively.
Older Triton images need a generate_stream translation; that path is
implemented here so Phase 4 can flip `openai_compatible: false`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.routing import ConcreteRoute
from app.schemas import ChatCompletionRequest, ChatMessage


def messages_to_prompt(messages: Iterable[ChatMessage]) -> str:
    parts: list[str] = []
    for message in messages:
        content = message.content
        if content is None:
            text = ""
        elif isinstance(content, list):
            text = " ".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in content
            )
        else:
            text = content
        parts.append(f"{message.role}: {text}")
    parts.append("assistant:")
    return "\n".join(parts)


def openai_payload(body: ChatCompletionRequest, route: ConcreteRoute) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    payload["model"] = route.upstream_model or body.model
    payload.pop("extra", None)
    extras = body.model_extra or {}
    payload.update(extras)
    return payload


def triton_generate_payload(body: ChatCompletionRequest, route: ConcreteRoute) -> dict[str, Any]:
    max_tokens = body.max_tokens or body.max_completion_tokens or 256
    return {
        "text_input": messages_to_prompt(body.messages),
        "max_tokens": max_tokens,
        "stream": body.stream,
        "temperature": body.temperature if body.temperature is not None else 0.0,
        "top_p": body.top_p if body.top_p is not None else 1.0,
        "model_name": route.upstream_model or body.model,
    }


def chat_url(route: ConcreteRoute) -> str:
    return route.url.rstrip("/") + "/v1/chat/completions"


def upstream_url(route: ConcreteRoute, body: ChatCompletionRequest) -> str:
    if route.openai_compatible:
        return chat_url(route)
    name = route.upstream_model or body.model
    method = "generate_stream" if body.stream else "generate"
    return f"{route.url.rstrip('/')}/v2/models/{name}/{method}"


def upstream_payload(route: ConcreteRoute, body: ChatCompletionRequest) -> dict[str, Any]:
    if route.openai_compatible:
        return openai_payload(body, route)
    return triton_generate_payload(body, route)
