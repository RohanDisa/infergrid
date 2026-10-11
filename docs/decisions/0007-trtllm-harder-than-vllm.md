# ADR 0007: What is harder about Triton + TensorRT-LLM than vLLM

*Status: accepted from the spec and NVIDIA support matrix (2026-10-10)*

This ADR is written from the implementation plan, not from a successful L4
engine load. Update it after the first real `trtllm-build`.

## Context

vLLM is an OpenAI server plus a checkpoint path. Triton + TRT-LLM is an
engine build, a four-model repository, and a version pin between the NGC
build image and the serve image.

## Decision

Build engines only inside `nvcr.io/nvidia/tritonserver:26.07-trtllm-python-py3`
(TRT-LLM 1.2.1). Fill `inflight_batcher` templates with
`model_prep.trtllm.fill_template`. Enable `decoupled_mode` for streaming /
TTFT. Match vLLM's 0.90 memory fraction via `kv_cache_free_gpu_mem_fraction`.

## Why this is harder

- Engine ABI must match the serve image. Mismatch is the most common failure.
- `g2-standard-8` (32 GB RAM) can OOM during `trtllm-build`; use
  `g2-standard-12` for the Job.
- The model repo is four models (preprocess, engine, postprocess, ensemble),
  not one `--model` flag.
- OpenAI frontend may be missing; the gateway already has a generate_stream
  adapter (`openai_compatible: false`).
