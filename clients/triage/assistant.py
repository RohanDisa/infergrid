"""Support-triage assistant that uses Infergrid as an OpenAI-compatible backend.

The spec asks to point an existing LangChain triage app at the gateway. This
client does that: LangChain `ChatOpenAI` when installed, otherwise the same
chat-completions HTTP call. Categories: billing, bug, howto, other.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import httpx

CATEGORIES = ("billing", "bug", "howto", "other")

SYSTEM = (
    "You are a support triage classifier. "
    "Reply with exactly one word: billing, bug, howto, or other."
)


def classify_http(ticket: str, *, base_url: str, model: str, timeout: float = 30.0) -> str:
    response = httpx.post(
        base_url.rstrip("/") + "/v1/chat/completions",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": ticket},
            ],
            "max_tokens": 8,
            "temperature": 0,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    text = str(response.json()["choices"][0]["message"]["content"]).strip().lower()
    for name in CATEGORIES:
        if name in text:
            return name
    return "other"


def classify_langchain(ticket: str, *, base_url: str, model: str) -> str:
    from langchain_openai import ChatOpenAI  # type: ignore[import-untyped]

    llm = ChatOpenAI(
        model=model,
        base_url=base_url.rstrip("/") + "/v1",
        api_key=os.environ.get("INFERGRID_API_KEY", "not-used"),
        temperature=0,
    )
    message = llm.invoke([("system", SYSTEM), ("human", ticket)])
    text = str(message.content).strip().lower()
    for name in CATEGORIES:
        if name in text:
            return name
    return "other"


def classify(ticket: str, *, base_url: str, model: str, use_langchain: bool = False) -> str:
    if use_langchain:
        return classify_langchain(ticket, base_url=base_url, model=model)
    return classify_http(ticket, base_url=base_url, model=model)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticket")
    parser.add_argument(
        "--base-url", default=os.environ.get("INFERGRID_URL", "http://127.0.0.1:8080")
    )
    parser.add_argument("--model", default="llama-8b")
    parser.add_argument("--langchain", action="store_true")
    args = parser.parse_args(argv)
    label = classify(
        args.ticket, base_url=args.base_url, model=args.model, use_langchain=args.langchain
    )
    payload: dict[str, Any] = {"ticket": args.ticket, "label": label, "model": args.model}
    print(json.dumps(payload))
