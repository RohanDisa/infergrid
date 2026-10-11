# Architecture

Clients send OpenAI-compatible `POST /v1/chat/completions` to the gateway.
The gateway looks up the `model` field (or `x-backend`) in a hot-reloaded
ConfigMap and streams the request to either vLLM or Triton.

```
Client  ->  Gateway  ->  vLLM pods   ->  PVC weight cache  <-  GCS
                     ->  Triton pods ->  PVC engine cache  <-  GCS

Prometheus scrapes gateway, backends, and DCGM.
KEDA reads llm_queue_depth and scales backend Deployments 1..2.
GKE cluster autoscaler adds L4 nodes when GPU pods stay Pending.
```

Local Kind replaces GPU backends with `mock-backend`, which speaks the same
OpenAI and `/metrics` contracts so charts, probes, and KEDA can be debugged
without spending GPU credits.

See `README.md` for the request-flow diagram and `docs/decisions/` for why
each layer was chosen.
