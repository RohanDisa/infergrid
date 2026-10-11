# ADR 0008: Custom gateway vs Kubernetes Gateway API Inference Extension

*Status: accepted (2026-10-10)*

## Context

The Gateway API Inference Extension does model-aware load balancing using KV
cache and queue signals. Infergrid already has a small FastAPI router.

## Decision

Keep the FastAPI gateway for this project. It is testable without CRDs, owns
the OpenAI contract and Triton adapter, and is the right size for one model
family. Revisit the Inference Extension when there are many replicas and
prefix-cache-aware routing matters.

## Comparison

| | FastAPI gateway | Inference Extension |
| --- | --- | --- |
| OpenAI `/v1/chat/completions` | Yes | Via backend |
| Weighted A/B by model name | Yes | Not the main job |
| KV / queue-aware LB | No | Yes, that is the point |
| Extra cluster CRDs | No | Yes |
| Works on `make dev` | Yes | No |

The custom gateway is the control plane for *which model*. The Inference
Extension would be the data plane for *which replica*. They compose; they
are not substitutes.
