#!/usr/bin/env python3
"""Drive concurrent chat completions so the local KEDA ScaledObject can fire."""

from __future__ import annotations

import argparse
import asyncio
import time

import httpx


async def _one(client: httpx.AsyncClient, url: str, model: str, tokens: int) -> int:
    response = await client.post(
        f"{url.rstrip('/')}/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": "keep the queue busy"}],
            "max_tokens": tokens,
        },
        timeout=60.0,
    )
    return response.status_code


async def _worker(
    client: httpx.AsyncClient,
    url: str,
    model: str,
    tokens: int,
    until: float,
    stats: dict[str, int],
) -> None:
    while time.time() < until:
        try:
            status = await _one(client, url, model, tokens)
            key = "ok" if status < 400 else "err"
        except httpx.HTTPError:
            key = "err"
        stats[key] = stats.get(key, 0) + 1


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="mock-qwen")
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--max-tokens", type=int, default=24)
    args = parser.parse_args()

    stats: dict[str, int] = {"ok": 0, "err": 0}
    until = time.time() + args.seconds
    limits = httpx.Limits(max_connections=args.concurrency + 4)
    async with httpx.AsyncClient(limits=limits) as client:
        workers = [
            asyncio.create_task(
                _worker(client, args.url, args.model, args.max_tokens, until, stats)
            )
            for _ in range(args.concurrency)
        ]
        await asyncio.gather(*workers)
    print(f"done ok={stats['ok']} err={stats['err']} concurrency={args.concurrency}")


if __name__ == "__main__":
    asyncio.run(main())
