# ADR 0004: Small FastAPI gateway instead of LiteLLM

*Status: accepted (2026-10-10)*

## Context

Clients need one OpenAI URL in front of vLLM and Triton. LiteLLM already
does this. A custom service is more code to maintain.

## Decision

Write a small FastAPI proxy (~few hundred lines) with a hot-reloaded route
table, weighted aliases, `x-backend` override, connect-only retry, and
streaming pass-through. Unit tests mock upstreams.

## Consequences

We own the latency overhead (target: p50 under 5 ms) and the metrics names.
We do not get LiteLLM's provider ecosystem. If Triton lacks an OpenAI
frontend in the pinned image, the gateway already has a generate_stream
adapter. A later ADR can compare this to the Kubernetes Gateway API
Inference Extension.
