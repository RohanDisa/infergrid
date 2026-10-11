# Benchmark run log

Every published number in the README must have a row here.

| Date | Commit | GPU / driver | CUDA | Images | Engine / server flags | Workload | Concurrency | Client | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | | | Phase 8: first real run |

Template for a run:

```
date:
git_commit:
gpu: NVIDIA L4 24GB
driver:
cuda:
spot_or_ondemand:
vllm_image: vllm/vllm-openai:v0.31.0
triton_image: nvcr.io/nvidia/tritonserver:26.07-trtllm-python-py3
engine_flags:
server_flags:
workload: chat 512/256
concurrency: 32
client: aiperf <version>
```
