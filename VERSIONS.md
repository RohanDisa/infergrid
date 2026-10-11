# Pinned versions

Recorded 2026-10-10. Re-check NGC, Docker Hub, and Artifact Hub before any GPU benchmark
run, then copy the pins that were actually used into `bench/RUN_LOG.md`.

Do not trust versions from memory. This file is the source of truth for the repo.

## Model

| Item | Pin | Notes |
| --- | --- | --- |
| Primary (GKE) | `meta-llama/Llama-3.1-8B-Instruct` | License-gated; needs `HF_TOKEN` |
| Fallback (GKE) | `Qwen/Qwen2.5-7B-Instruct` | No license gate |
| Local / CI tiny | `Qwen/Qwen2.5-0.5B-Instruct` | CPU-optional; Phase 0 uses the mock instead |
| HF revision | _fill at download time_ | Store the commit hash in `model-prep/manifest.json` |
| `max_model_len` | `4096` | Fixed for every benchmark config |

## Serving backends

| Item | Pin | Notes |
| --- | --- | --- |
| vLLM | `0.31.0` (2026-10-05) | [vllm-project/vllm](https://github.com/vllm-project/vllm/releases) |
| vLLM GPU image | `vllm/vllm-openai:v0.31.0` | Default CUDA 13.0 |
| vLLM CUDA 12.9 image | `vllm/vllm-openai:v0.31.0-cu129` | Use if the L4 node image prefers 12.x |
| vLLM CPU image | `vllm/vllm-openai-cpu:v0.31.0` | Optional; Phase 0 uses `mock-backend` |
| Triton + TRT-LLM image | `nvcr.io/nvidia/tritonserver:26.07-trtllm-python-py3` | Latest `-trtllm-python-py3` in NVIDIA's compatibility matrix as of 2026-10-10 |
| TensorRT-LLM (in that image) | `1.2.1` | Must match the engine-build image |
| TensorRT (in that image) | `10.14.1.48` | |
| CUDA (in that image) | `13.1.0.036` | Driver `590.44.01` |
| Triton vLLM image (not used) | `nvcr.io/nvidia/tritonserver:26.09-vllm-python-py3` | Newer Triton line exists for vLLM; we serve vLLM directly |

The Triton getting-started docs mention `RELEASE=26.09` in places. The published
TRT-LLM compatibility table still tops out at `26.07`. Before Phase 4, confirm
the latest `-trtllm-python-py3` tag on NGC and update this file.

## Quantization

| Item | Pin | Notes |
| --- | --- | --- |
| AutoAWQ / llm-compressor | _fill at Phase 2_ | INT4 AWQ for vLLM |
| NVIDIA ModelOpt | shipped in TRT-LLM `1.2.1` image | FP8 (and optional INT4) for TRT-LLM |
| Calibration set | _fill at Phase 2_ | ~512 public samples; record the dataset + seed |

## Kubernetes and cloud

| Item | Pin | Notes |
| --- | --- | --- |
| Local cluster | kind `v0.27.x` or newer | `infra/local/kind.yaml` |
| kind node image | `kindest/node:v1.34.0` | Matches current kind defaults; bump with kind |
| GKE channel | `regular` | Default at record time: `1.35.7-gke.1150000` |
| GPU machine | `g2-standard-8` (1x L4, 24 GB) | Spot for iteration; on-demand for final benches |
| Build-job machine | `g2-standard-12` | Extra RAM for `trtllm-build` |
| Helm | `3.16+` | |
| kubectl | matching cluster minor | |

## Observability and autoscaling

| Item | Pin | Notes |
| --- | --- | --- |
| kube-prometheus-stack | Helm `92.2.0` (2026-10-08) | Prometheus Operator `v0.94.1` |
| KEDA | Helm / app `2.21.0` (2026-09-23) | Review the 2.21 token-audience migration if you customize RBAC |
| DCGM Exporter | `4.8.4` (2026-09-18) | Chart repo: `https://nvidia.github.io/dcgm-exporter/helm-charts` |
| DCGM library | `4.6.1` | Bundled with exporter 4.8.4 |

## Benchmarking

| Item | Pin | Notes |
| --- | --- | --- |
| Primary client | [AIPerf](https://github.com/ai-dynamo/aiperf) | Successor to GenAI-Perf; see ADR 0005 |
| GenAI-Perf image | `nvcr.io/nvidia/eval-factory/genai-perf:26.03` | Frozen fallback only |
| Cross-check | `vllm bench serve` from vLLM `0.31.0` | |
| lm-evaluation-harness | _fill at Phase 2_ | GSM8K 250 + MMLU subset |

## Gateway and mock (this repo)

| Item | Pin |
| --- | --- |
| Python | `3.11` (local), `3.12-slim` (images) |
| FastAPI | `>=0.115` |
| httpx | `>=0.27` |
| uvicorn | `>=0.32` |

## How to refresh

```bash
# vLLM
curl -s https://api.github.com/repos/vllm-project/vllm/releases/latest | jq -r .tag_name

# Triton TRT-LLM tags
# https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/introduction/compatibility.html

# Helm charts
helm repo update
helm search repo prometheus-community/kube-prometheus-stack --versions | head
helm search repo kedacore/keda --versions | head
```
