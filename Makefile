# Infergrid — local Kind cluster, charts, and later GKE/bench targets.
# Run from the repo root. On Windows use Git Bash, WSL, or scripts/local-up.ps1.

SHELL := /bin/bash
.DEFAULT_GOAL := help

CLUSTER        ?= infergrid
NAMESPACE      ?= infergrid
GATEWAY_IMAGE  ?= infergrid/gateway:dev
MOCK_IMAGE     ?= infergrid/mock-backend:dev
KUBE_CONTEXT   ?= kind-$(CLUSTER)

PROM_CHART     ?= 92.2.0
KEDA_CHART     ?= 2.21.0

.PHONY: help venv lint test helm-lint dev images local-up local-down \
	smoke load cluster-up cluster-down deploy-vllm deploy-gateway

help:
	@echo "Infergrid targets"
	@echo "  make venv          create .venv and install gateway + test deps"
	@echo "  make lint          ruff + mypy"
	@echo "  make test          pytest (gateway + mock)"
	@echo "  make helm-lint     helm lint + helm template every chart"
	@echo "  make dev           mock + gateway on the host (no Docker)"
	@echo "  make images        build gateway and mock-backend images"
	@echo "  make local-up      optional Kind cluster (heavy; skip on a thin laptop)"
	@echo "  make smoke         curl the gateway (default http://127.0.0.1:8080)"
	@echo "  make load          generate load against the gateway"
	@echo "  make local-down    delete the kind cluster"
	@echo "  make cluster-up    create the GKE cluster (infra/gke/up.sh)"
	@echo "  make cluster-down  scale GPU pool to 0 (infra/gke/down.sh)"

venv:
	python -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e ".[dev]"

lint:
	ruff check gateway mock-backend bench model_prep clients edge scripts
	ruff format --check gateway mock-backend bench model_prep clients edge scripts
	mypy

test:
	pytest -q

dev:
	python scripts/dev_up.py

helm-lint:
	@for chart in charts/gateway charts/mock-backend charts/vllm charts/triton-trtllm charts/autoscaling; do \
		echo "==> helm lint $$chart"; \
		helm lint $$chart; \
		echo "==> helm template $$chart"; \
		helm template infergrid-$$(basename $$chart) $$chart --namespace $(NAMESPACE) >/dev/null; \
	done

images:
	docker build -t $(GATEWAY_IMAGE) gateway
	docker build -t $(MOCK_IMAGE) mock-backend

local-up: images
	bash infra/local/up.sh

local-down:
	bash infra/local/down.sh

smoke:
	bash scripts/smoke.sh

load:
	python scripts/load.py --url $${INFERGRID_URL:-http://127.0.0.1:8080} --concurrency 16 --seconds 90

cluster-up:
	bash infra/gke/up.sh

cluster-down:
	bash infra/gke/down.sh

deploy-gateway:
	helm upgrade --install gateway charts/gateway \
		--namespace $(NAMESPACE) --create-namespace \
		-f charts/gateway/values-local.yaml

deploy-vllm:
	@echo "Set CONFIG=fp16|awq|fp8 and ensure the GKE context is active."
	helm upgrade --install vllm-$${CONFIG:-fp16} charts/vllm \
		--namespace $(NAMESPACE) --create-namespace \
		-f charts/vllm/values.yaml \
		-f charts/vllm/values-$${CONFIG:-fp16}.yaml
