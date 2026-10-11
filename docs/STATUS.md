# Phase status

Code for every spec phase is in the repo. GPU / GKE / Kind were not executed
on the author laptop. Tests cover the laptop-safe parts.

| Phase | Spec | Code | Tests | Executed |
| --- | --- | --- | --- | --- |
| 0 | Kind + mock + gateway + Prom + KEDA | Yes (`make dev`; Kind optional) | gateway, mock | pytest yes; Kind no |
| 1 | GKE L4 pool + budget | `infra/gke/` | — | No |
| 2 | Five artifacts + accuracy | `model_prep/` | manifest, quant, eval, download | Dry-run / smoke |
| 3 | vLLM chart | `charts/vllm/` | helm lint | No deploy |
| 4 | Triton + TRT-LLM | chart + repo + `build_engine.sh` | fill_template | No engine build |
| 5 | Gateway + triage client | `gateway/`, `clients/triage/` | yes | `make dev` |
| 6 | Prom / Grafana / DCGM | values + dashboard JSON | — | No |
| 7 | KEDA queue depth | `charts/autoscaling/` | helm lint | No |
| 8 | Bench matrix + AIPerf | `bench/` | aiperf, sanity, matrix | Dry-run |
| 9 | CI/CD | `.github/workflows/` | — | No remote |
| 10 | Edge | `edge/simulate.py` | yes | Args only |
