#!/usr/bin/env bash
# Scale the GPU pool to zero. Does not delete the cluster (CPU node still bills).
# To delete everything: DELETE_CLUSTER=1 make cluster-down
set -euo pipefail

PROJECT="${PROJECT:-${GOOGLE_CLOUD_PROJECT:-}}"
ZONE="${ZONE:-us-central1-a}"
CLUSTER="${CLUSTER:-infergrid}"

if [[ -z "$PROJECT" ]]; then
  echo "Set PROJECT or GOOGLE_CLOUD_PROJECT" >&2
  exit 1
fi

gcloud config set project "$PROJECT"

if [[ "${DELETE_CLUSTER:-0}" == "1" ]]; then
  echo "==> deleting cluster $CLUSTER"
  gcloud container clusters delete "$CLUSTER" --zone "$ZONE" --quiet
  exit 0
fi

echo "==> scaling gpu-l4 to 0 nodes"
gcloud container clusters update "$CLUSTER" --zone "$ZONE" \
  --node-pool gpu-l4 --min-nodes 0 --max-nodes 2 --quiet || true
gcloud container clusters resize "$CLUSTER" --zone "$ZONE" \
  --node-pool gpu-l4 --num-nodes 0 --quiet
echo "GPU pool scaled to 0. System node is still running; delete the cluster if you are pausing for a week."
