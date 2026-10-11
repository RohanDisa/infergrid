#!/usr/bin/env bash
set -euo pipefail
CLUSTER="${CLUSTER:-infergrid}"
echo "==> deleting kind cluster $CLUSTER"
kind delete cluster --name "$CLUSTER"
