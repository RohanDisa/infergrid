# Infergrid

Cloud-native LLM serving on Kubernetes with a unified OpenAI-compatible gateway for **vLLM** and **NVIDIA Triton + TensorRT-LLM**, queue-based autoscaling, and an NVIDIA L4 benchmarking workflow.

## Features

- **Unified API:** streaming chat completions, weighted model aliases, and explicit backend selection.
- **Model optimization:** FP16, FP8, and AWQ INT4 preparation workflows.
- **Kubernetes infrastructure:** Helm charts, GKE configuration, and KEDA autoscaling on queue depth.
- **Observability:** Prometheus metrics, NVIDIA DCGM monitoring, and Grafana dashboards.
- **Benchmarking:** AIPerf workloads for latency, throughput, accuracy comparison, and token-cost analysis.
- **Local development:** a GPU-free mock backend and LangChain support-triage client.

## Architecture

Clients send requests to the gateway, which routes by model name, weighted alias, or `x-backend` header to vLLM or Triton. Model weights and TensorRT engines use persistent volumes. Prometheus supplies queue-depth metrics to KEDA for inference replica scaling; GKE manages GPU node scaling.

The gateway exposes `/v1/chat/completions`, `/v1/models`, `/healthz`, `/readyz`, and `/metrics`.

## Quick Start

Run locally without Docker or a GPU (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python scripts/dev_up.py
```

The gateway runs at `http://127.0.0.1:8080` with a synthetic inference backend. In a second terminal, activate the environment and run:

```powershell
python -m clients.triage.assistant "I was charged twice" --model mock-qwen
```

## GKE Deployment

```bash
export PROJECT=your-gcp-project ZONE=us-central1-a
make cluster-up
kubectl apply -f infra/gke/gpu-smoke.yaml
make deploy-vllm CONFIG=fp16
```

Remove the environment when finished:

```bash
make cluster-down
```

For local Kubernetes, use `make local-up`; the gateway is exposed on port `18080`.

## Benchmarks

The benchmark matrix compares backend and precision configurations at concurrency levels **1, 8, 32, and 64**, using chat and RAG workloads. Each configuration specifies 30 warmup requests, 300 measured requests, and three repetitions with median aggregation.

With a serving backend running and AIPerf on `PATH`:

```bash
python -m bench.run_bench --config bench/configs/vllm-fp16-c32-chat.yaml --execute
python -m bench.make_table
```

Reports cover time to first token, inter-token latency, output throughput, KV-cache capacity, accuracy, and estimated cost per million tokens. 

## Testing and CI

```bash
pytest -q
```

Tests cover gateway behavior, routing, streaming, model preparation, and benchmark tooling. 
