# Cost controls

Do this in the GCP console before the first GPU node starts.

1. Billing, Budgets & alerts: budget `$250`, alerts at 20 / 50 / 80 / 100 percent.
2. Quotas: request `GPUS_ALL_REGIONS=1`, `NVIDIA_L4_GPUS=1`, and `PREEMPTIBLE_NVIDIA_L4_GPUS=1` in `us-central1`.
3. Trial accounts often block GPUs until you upgrade to paid. Credits still apply first.
4. After every GPU session: `make cluster-down`.
5. During idle weeks: `DELETE_CLUSTER=1 make cluster-down`.
6. Final published benches may use on-demand to avoid spot preemption; everything else is spot.
7. GitHub Actions `nightly-scale-down.yml` is the backstop for a forgotten GPU node.

Check current L4 prices in the GCP calculator for your region before Phase 1.
