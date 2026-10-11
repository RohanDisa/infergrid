#!/usr/bin/env bash
# Create the GKE cluster and a scale-to-zero L4 GPU pool.
# Review flags against current GKE docs before running. This spends credits.
set -euo pipefail

PROJECT="${PROJECT:-${GOOGLE_CLOUD_PROJECT:-}}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-a}"
CLUSTER="${CLUSTER:-infergrid}"
SYSTEM_MACHINE="${SYSTEM_MACHINE:-e2-standard-4}"
GPU_MACHINE="${GPU_MACHINE:-g2-standard-8}"
GPU_TYPE="${GPU_TYPE:-nvidia-l4}"
GPU_MAX="${GPU_MAX:-2}"

if [[ -z "$PROJECT" ]]; then
  echo "Set PROJECT or GOOGLE_CLOUD_PROJECT" >&2
  exit 1
fi

echo "==> project $PROJECT zone $ZONE"
gcloud config set project "$PROJECT"

gcloud services enable \
  compute.googleapis.com \
  container.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com

if ! gcloud container clusters describe "$CLUSTER" --zone "$ZONE" >/dev/null 2>&1; then
  echo "==> creating cluster $CLUSTER"
  gcloud container clusters create "$CLUSTER" \
    --zone "$ZONE" \
    --num-nodes 1 \
    --machine-type "$SYSTEM_MACHINE" \
    --release-channel regular \
    --workload-pool="${PROJECT}.svc.id.goog"
else
  echo "==> cluster $CLUSTER already exists"
fi

if ! gcloud container node-pools describe gpu-l4 --cluster "$CLUSTER" --zone "$ZONE" >/dev/null 2>&1; then
  echo "==> creating gpu-l4 pool (min 0, max $GPU_MAX, spot)"
  gcloud container node-pools create gpu-l4 \
    --cluster "$CLUSTER" \
    --zone "$ZONE" \
    --machine-type "$GPU_MACHINE" \
    --accelerator "type=${GPU_TYPE},count=1,gpu-driver-version=latest" \
    --spot \
    --num-nodes 0 \
    --enable-autoscaling --min-nodes 0 --max-nodes "$GPU_MAX" \
    --node-taints nvidia.com/gpu=present:NoSchedule
else
  echo "==> gpu-l4 pool already exists"
fi

BUCKET="${BUCKET:-${PROJECT}-models}"
if ! gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1; then
  echo "==> creating bucket gs://${BUCKET}"
  gcloud storage buckets create "gs://${BUCKET}" --location "$REGION"
fi

gcloud container clusters get-credentials "$CLUSTER" --zone "$ZONE"
echo "Cluster ready. GPU pool is at 0 nodes until a GPU pod is scheduled."
echo "Verify with: kubectl apply -f infra/gke/gpu-smoke.yaml && kubectl logs -f job/gpu-smoke"
echo "Tear down GPU spend with: make cluster-down"
