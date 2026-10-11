# ADR 0002: NVIDIA L4 on GKE as the single benchmark GPU

*Status: accepted (2026-10-10)*

## Context

The project needs one GPU type so every backend × precision cell is comparable,
and the budget is a $300 GCP trial with a $250 hard cap.

## Decision

Benchmark on a single L4 (24 GB, Ada, native FP8) via GKE `g2-standard-8`,
spot, pool min 0 / max 2, tainted `nvidia.com/gpu=present:NoSchedule`.
Use `g2-standard-12` only for TRT-LLM engine-build Jobs if 32 GB RAM is tight.

## Consequences

No multi-GPU or H100 story in the published table. Cold start includes node
provisioning. Spot preemption is a measurement risk; final runs may switch to
on-demand and must be labeled in `bench/RUN_LOG.md`.
