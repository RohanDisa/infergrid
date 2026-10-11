# ADR 0006: Do not require Kind on a thin laptop

*Status: accepted (2026-10-10)*

## Context

Phase 0 originally meant a 3-node Kind cluster plus kube-prometheus-stack and
KEDA. On this Windows laptop the Kind control-plane container sat at 130–200%
CPU, Docker Desktop was flaky, and a half-created cluster made
kube-controller-manager spin.

## Decision

The default local path is `make test` and `make dev` (uvicorn mock + gateway).
Kind remains in the repo as an optional chart-integration target, defaulting
to one node, with Prometheus off unless you opt in. Real serving, GPUs, and
benchmarks run on GKE later, not on the laptop.

## Consequences

You can review and extend the platform without Docker. You cannot demo KEDA
or Grafana until you use a stronger machine or GKE. The README must not claim
those demos were run here.
