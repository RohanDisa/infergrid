# ADR 0001: Mock OpenAI backend for Phase 0

*Status: accepted (2026-10-10)*

## Context

Phase 0 must exercise Helm charts, probes, Prometheus scrapes, and KEDA on a
laptop. vLLM publishes a CPU image (`vllm/vllm-openai-cpu:v0.31.0`), but it
is large, slow to pull in CI, and still not representative of GPU serving.

## Decision

Ship a tiny FastAPI mock that implements `/v1/chat/completions`, Triton
`generate[_stream]`, `/health`, and vLLM-shaped Prometheus metrics
(`vllm:num_requests_waiting`, KV cache, TTFT/ITL histograms). Kind and GitHub
Actions use this image. GKE replaces it with real vLLM / Triton charts.

## Consequences

Local numbers are synthetic and must never appear in the benchmark table.
The mock's queue gauge is real (an in-process semaphore), so KEDA scaling
behavior is a valid Kubernetes demo even though the "GPU" is fake.
