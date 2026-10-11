# ADR 0003: Autoscale on queue depth, not CPU or GPU util

*Status: accepted (2026-10-10)*

## Context

GPU inference pods sit at low CPU even when the GPU is saturated. GPU
utilization also stays high once the model is loaded, so it is a poor scale
signal. Queue depth (waiting requests) and KV-cache pressure are the signals
that predict TTFT SLO violations.

## Decision

KEDA Prometheus trigger on `llm_queue_depth` (normalized from vLLM waiting
requests and TRT-LLM queue metrics). Threshold will be set from Phase 8
data: the concurrency where p95 TTFT crosses the SLO, minus a small margin.
GKE cluster autoscaler adds L4 nodes when the extra replica cannot schedule.

## Consequences

Need recording rules so one query works for both backends. Cold start (node +
image + model load) is minutes, so demos keep `minReplicaCount: 1` and treat
scale-to-zero as an idle cost optimization with the cold-start number stated.
