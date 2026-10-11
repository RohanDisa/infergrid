#!/usr/bin/env bash
# Create a Kind cluster and install the Phase 0 stack: Prometheus, KEDA, mock, gateway.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLUSTER="${CLUSTER:-infergrid}"
NAMESPACE="${NAMESPACE:-infergrid}"
GATEWAY_IMAGE="${GATEWAY_IMAGE:-infergrid/gateway:dev}"
MOCK_IMAGE="${MOCK_IMAGE:-infergrid/mock-backend:dev}"
PROM_CHART="${PROM_CHART:-92.2.0}"
KEDA_CHART="${KEDA_CHART:-2.21.0}"
# Default off: Prometheus on Kind pinned this laptop. Set to 0 to opt in.
SKIP_OBSERVABILITY="${SKIP_OBSERVABILITY:-1}"

cd "$ROOT"

if ! command -v kind >/dev/null; then
  echo "kind is required: https://kind.sigs.k8s.io/docs/user/quick-start/" >&2
  exit 1
fi
if ! command -v helm >/dev/null; then
  echo "helm is required: https://helm.sh/docs/intro/install/" >&2
  exit 1
fi

if ! kind get clusters | grep -qx "$CLUSTER"; then
  echo "==> creating kind cluster $CLUSTER"
  kind create cluster --name "$CLUSTER" --config infra/local/kind.yaml
else
  echo "==> kind cluster $CLUSTER already exists"
fi

echo "==> loading images"
kind load docker-image "$GATEWAY_IMAGE" --name "$CLUSTER"
kind load docker-image "$MOCK_IMAGE" --name "$CLUSTER"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

if [[ "$SKIP_OBSERVABILITY" != "1" ]]; then
  echo "==> kube-prometheus-stack $PROM_CHART"
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
  helm repo update prometheus-community >/dev/null
  helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
    --namespace monitoring --create-namespace \
    --version "$PROM_CHART" \
    -f charts/observability/values-prometheus-local.yaml \
    --wait --timeout 10m
  kubectl apply -f charts/observability/recording-rules.yaml
  kubectl -n monitoring create configmap infergrid-grafana-dashboard \
    --from-file=infergrid.json="$ROOT/dashboards/infergrid.json" \
    --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n monitoring label configmap infergrid-grafana-dashboard grafana_dashboard=1 --overwrite
fi

echo "==> KEDA $KEDA_CHART"
helm repo add kedacore https://kedacore.github.io/charts >/dev/null
helm repo update kedacore >/dev/null
helm upgrade --install keda kedacore/keda \
  --namespace keda --create-namespace \
  --version "$KEDA_CHART" \
  --wait --timeout 5m

echo "==> mock backend + gateway"
helm upgrade --install mock-backend charts/mock-backend \
  --namespace "$NAMESPACE" \
  --set image.repository="$(echo "$MOCK_IMAGE" | cut -d: -f1)" \
  --set image.tag="$(echo "$MOCK_IMAGE" | cut -d: -f2)"
helm upgrade --install gateway charts/gateway \
  --namespace "$NAMESPACE" \
  -f charts/gateway/values-local.yaml \
  --set image.repository="$(echo "$GATEWAY_IMAGE" | cut -d: -f1)" \
  --set image.tag="$(echo "$GATEWAY_IMAGE" | cut -d: -f2)"

echo "==> KEDA ScaledObject"
helm upgrade --install infergrid-autoscaling charts/autoscaling --namespace "$NAMESPACE"

echo "==> waiting for rollout"
kubectl -n "$NAMESPACE" rollout status deploy/mock-backend --timeout=180s
kubectl -n "$NAMESPACE" rollout status deploy/gateway --timeout=180s

cat <<EOF

Kind cluster is up.

  Gateway:    http://127.0.0.1:18080
  Prometheus: http://127.0.0.1:9090
  Grafana:    http://127.0.0.1:3000  (admin / infergrid)

Smoke test:
  make smoke
  # or: curl http://127.0.0.1:18080/v1/models

Scale demo:
  make load
  kubectl -n $NAMESPACE get deploy mock-backend -w
EOF
