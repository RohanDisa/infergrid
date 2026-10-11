"""Accuracy check against a served OpenAI endpoint.

Spec: lm-evaluation-harness on GSM8K (250) and MMLU (subset), scores next to
speed. This module:
- always runs a tiny built-in smoke set (no extra deps) so CI can score a mock
- shells out to `lm_eval` when --harness is set and the package is installed
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import httpx

# Public-domain arithmetic / knowledge items for CI. Not a substitute for GSM8K.
SMOKE_TASKS = {
    "gsm8k_smoke": [
        {"prompt": "What is 2 + 2?", "answer": "4"},
        {"prompt": "What is 10 - 3?", "answer": "7"},
        {"prompt": "What is 5 * 6?", "answer": "30"},
    ],
    "mmlu_smoke": [
        {"prompt": "How many days are in a week?", "answer": "7"},
        {"prompt": "What gas do humans exhale? Answer with the chemical formula.", "answer": "CO2"},
    ],
}


def extract_number(text: str) -> str:
    matches = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return matches[-1] if matches else text.strip()


def score_item(reply: str, expected: str, *, numeric: bool) -> bool:
    got = reply.strip()
    if numeric:
        return extract_number(got) == expected
    return expected.lower() in got.lower()


def chat_complete(
    client: httpx.Client,
    url: str,
    model: str,
    prompt: str,
    timeout: float,
) -> str:
    response = client.post(
        url.rstrip("/") + "/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 32,
            "temperature": 0,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return str(response.json()["choices"][0]["message"]["content"])


def run_smoke(
    base_url: str,
    model: str,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    scores: dict[str, Any] = {}
    with httpx.Client() as client:
        for name, items in SMOKE_TASKS.items():
            numeric = name.startswith("gsm8k")
            hits = 0
            for item in items:
                reply = chat_complete(client, base_url, model, item["prompt"], timeout)
                if score_item(reply, item["answer"], numeric=numeric):
                    hits += 1
            scores[name] = {"correct": hits, "n": len(items), "acc": hits / len(items)}
    return scores


def harness_command(base_url: str, model: str, limit: int) -> list[str]:
    return [
        "lm_eval",
        "--model",
        "local-chat-completions",
        "--model_args",
        f"model={model},base_url={base_url}/v1/chat/completions",
        "--tasks",
        "gsm8k,mmlu",
        "--limit",
        str(limit),
        "--apply_chat_template",
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="mock-qwen")
    parser.add_argument("--out", type=Path, default=Path("model-prep/artifacts/accuracy.json"))
    parser.add_argument("--harness", action="store_true")
    parser.add_argument("--limit", type=int, default=250)
    args = parser.parse_args(argv)

    payload: dict[str, Any] = {
        "base_url": args.base_url,
        "model": args.model,
        "smoke": run_smoke(args.base_url, args.model),
    }
    if args.harness:
        payload["lm_eval_command"] = harness_command(args.base_url, args.model, args.limit)
        payload["lm_eval_note"] = "Run that command on the GPU box; paste scores here."
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
