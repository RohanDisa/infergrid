# ADR 0005: AIPerf as the primary benchmark client

*Status: accepted (2026-10-10)*

## Context

The original plan named NVIDIA GenAI-Perf. NVIDIA is phasing GenAI-Perf out
and points new work at [AIPerf](https://github.com/ai-dynamo/aiperf). The
last GenAI-Perf eval-factory image at record time is `26.03`.

## Decision

Primary client: AIPerf (`aiperf profile`). Cross-check: `vllm bench serve`.
Keep the GenAI-Perf `26.03` image as a frozen fallback. `bench/run_bench.py`
is the only entry point that writes `bench/results/*.json`.

## Consequences

CLI flags differ (`--workers-max`, `--gpu-telemetry`). Record the exact
AIPerf version in `RUN_LOG.md` on the first real run. Do not mix GenAI-Perf
and AIPerf numbers in one table.
