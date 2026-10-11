from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response

MODEL_NAME = os.environ.get("MOCK_MODEL_NAME", "mock-qwen")
CAPACITY = int(os.environ.get("MOCK_CAPACITY", "1"))
TOKEN_DELAY_MS = int(os.environ.get("MOCK_TOKEN_DELAY_MS", "80"))
DEFAULT_TOKENS = int(os.environ.get("MOCK_DEFAULT_TOKENS", "16"))
KV_USAGE = float(os.environ.get("MOCK_KV_CACHE_USAGE", "0.35"))
DEPLOYMENT = os.environ.get("MOCK_DEPLOYMENT", "mock-backend")
_LABELS = {"deployment": DEPLOYMENT}

RUNNING = Gauge("vllm:num_requests_running", "Requests currently running (mock)", ["deployment"])
WAITING = Gauge("vllm:num_requests_waiting", "Requests waiting for a slot (mock)", ["deployment"])
KV_CACHE = Gauge("vllm:kv_cache_usage_perc", "Synthetic KV cache usage", ["deployment"])
TOKENS_OUT = Counter("vllm:generation_tokens_total", "Generated tokens", ["deployment"])
TOKENS_IN = Counter("vllm:prompt_tokens_total", "Prompt tokens (approx)", ["deployment"])
TTFT = Histogram(
    "vllm:time_to_first_token_seconds",
    "Time to first token",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
ITL = Histogram(
    "vllm:time_per_output_token_seconds",
    "Inter-token latency",
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5),
)


class Scheduler:
    def __init__(self, capacity: int) -> None:
        self.sem = asyncio.Semaphore(capacity)
        self.running = 0
        self.waiting = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            self.waiting += 1
            WAITING.labels(**_LABELS).set(self.waiting)
        await self.sem.acquire()
        async with self._lock:
            self.waiting -= 1
            self.running += 1
            WAITING.labels(**_LABELS).set(self.waiting)
            RUNNING.labels(**_LABELS).set(self.running)

    async def release(self) -> None:
        async with self._lock:
            self.running -= 1
            RUNNING.labels(**_LABELS).set(self.running)
        self.sem.release()


SCHEDULER = Scheduler(CAPACITY)


class ChatMessage(BaseModel):
    role: str
    content: str | None = None


class ChatRequest(BaseModel):
    model: str = MODEL_NAME
    messages: list[ChatMessage] = Field(default_factory=list)
    stream: bool = False
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    temperature: float | None = None


def _token_count(request: ChatRequest) -> int:
    requested = request.max_tokens or request.max_completion_tokens or DEFAULT_TOKENS
    return max(1, min(requested, 64))


def _prompt_preview(request: ChatRequest) -> str:
    for message in reversed(request.messages):
        if message.content:
            return message.content.strip()
    return "hello"


def _tokens_for(request: ChatRequest) -> list[str]:
    n = _token_count(request)
    preview = _prompt_preview(request).split()
    last = preview[-1] if preview else "ok"
    words = [f"{last}-ack"] + [f"tok{i}" for i in range(n - 1)]
    return words[:n]


def _completion_json(request: ChatRequest, tokens: list[str], created: int) -> dict[str, object]:
    text = " ".join(tokens)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": created,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": max(1, len(_prompt_preview(request).split())),
            "completion_tokens": len(tokens),
            "total_tokens": max(1, len(_prompt_preview(request).split())) + len(tokens),
        },
    }


def _sse_chunks(request: ChatRequest, tokens: list[str], created: int) -> Iterator[bytes]:
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    for index, token in enumerate(tokens):
        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": token + (" " if index < len(tokens) - 1 else ""),
                    },
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk)}\n\n".encode()
    final = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": request.model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(final)}\n\n".encode()
    yield b"data: [DONE]\n\n"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    RUNNING.labels(**_LABELS).set(0)
    WAITING.labels(**_LABELS).set(0)
    KV_CACHE.labels(**_LABELS).set(KV_USAGE)
    yield


app = FastAPI(title="infergrid-mock-backend", lifespan=lifespan)


@app.get("/health")
@app.get("/healthz")
@app.get("/v2/health/ready")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/models")
async def models() -> dict[str, object]:
    return {
        "object": "list",
        "data": [{"id": MODEL_NAME, "object": "model", "owned_by": "infergrid-mock"}],
    }


async def _run_completion(request: ChatRequest) -> tuple[list[str], int, float]:
    await SCHEDULER.acquire()
    started = time.perf_counter()
    try:
        TOKENS_IN.labels(**_LABELS).inc(max(1, len(_prompt_preview(request).split())))
        tokens = _tokens_for(request)
        delay = TOKEN_DELAY_MS / 1000.0
        await asyncio.sleep(delay)
        TTFT.observe(time.perf_counter() - started)
        for _ in tokens[1:]:
            token_started = time.perf_counter()
            await asyncio.sleep(delay)
            ITL.observe(time.perf_counter() - token_started)
        TOKENS_OUT.labels(**_LABELS).inc(len(tokens))
        return tokens, int(time.time()), time.perf_counter() - started
    finally:
        await SCHEDULER.release()


@app.post("/v1/chat/completions", response_model=None)
async def chat(request: ChatRequest) -> StreamingResponse | JSONResponse:
    if request.stream:
        await SCHEDULER.acquire()
        started = time.perf_counter()

        async def event_stream() -> AsyncIterator[bytes]:
            try:
                TOKENS_IN.labels(**_LABELS).inc(max(1, len(_prompt_preview(request).split())))
                tokens = _tokens_for(request)
                delay = TOKEN_DELAY_MS / 1000.0
                await asyncio.sleep(delay)
                TTFT.observe(time.perf_counter() - started)
                first = True
                for chunk in _sse_chunks(request, tokens, int(time.time())):
                    if not first:
                        token_started = time.perf_counter()
                        await asyncio.sleep(delay)
                        ITL.observe(time.perf_counter() - token_started)
                    first = False
                    yield chunk
                TOKENS_OUT.labels(**_LABELS).inc(len(tokens))
            finally:
                await SCHEDULER.release()

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    tokens, created, _elapsed = await _run_completion(request)
    return JSONResponse(_completion_json(request, tokens, created))


class GenerateRequest(BaseModel):
    text_input: str
    max_tokens: int = DEFAULT_TOKENS
    stream: bool = False
    temperature: float = 0.0
    top_p: float = 1.0
    model_name: str = MODEL_NAME


@app.post("/v2/models/{model_name}/generate", response_model=None)
@app.post("/v2/models/{model_name}/generate_stream", response_model=None)
async def generate(model_name: str, request: GenerateRequest) -> StreamingResponse | JSONResponse:
    chat_req = ChatRequest(
        model=model_name,
        messages=[ChatMessage(role="user", content=request.text_input)],
        stream=request.stream,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )
    if request.stream:

        async def event_stream() -> AsyncIterator[bytes]:
            tokens, _created, _elapsed = await _run_completion(chat_req)
            so_far = ""
            for token in tokens:
                so_far = (so_far + " " + token).strip()
                yield (
                    json.dumps({"model_name": model_name, "text_output": so_far}) + "\n"
                ).encode()

        return StreamingResponse(event_stream(), media_type="application/json")

    tokens, _created, _elapsed = await _run_completion(chat_req)
    return JSONResponse({"model_name": model_name, "text_output": " ".join(tokens)})
