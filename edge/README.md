# Edge (Phase 10, stretch)

Do this only after Phases 0–9.

## Option A: Jetson Orin Nano / NX

- Flash current JetPack, then use an engine that actually supports that
  JetPack (TensorRT-LLM for Jetson, llama.cpp, or MLC — check before you buy).
- Serve a 1B–3B instruct model in INT4. An 8B model will not fit comfortably
  in 8 GB shared memory.
- Optional: k3s so the same Helm chart pattern deploys to the device.
- Measure TTFT, tokens/s, and power (`tegrastats`). Report tokens per joule.

## Option B: no hardware

Simulate an 8 GB device on the L4 with `--gpu-memory-utilization 0.3` or use
a free Kaggle T4. Label the table as a simulation.

Tradeoffs to write up: edge wins on privacy, offline, and first-token latency
to a nearby user; cloud wins on tokens/s, larger context, and operational
toil.
