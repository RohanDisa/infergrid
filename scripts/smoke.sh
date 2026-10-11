#!/usr/bin/env bash
set -euo pipefail
BASE="${INFERGRID_URL:-http://127.0.0.1:8080}"

echo "==> GET $BASE/healthz"
curl -fsS "$BASE/healthz"
echo

echo "==> GET $BASE/v1/models"
curl -fsS "$BASE/v1/models"
echo

echo "==> POST $BASE/v1/chat/completions"
curl -fsS "$BASE/v1/chat/completions" \
  -H "content-type: application/json" \
  -d '{"model":"mock-qwen","messages":[{"role":"user","content":"say hello"}],"max_tokens":8}'
echo

echo "==> STREAM $BASE/v1/chat/completions"
curl -fsS "$BASE/v1/chat/completions" \
  -H "content-type: application/json" \
  -d '{"model":"llama-8b","messages":[{"role":"user","content":"stream please"}],"stream":true,"max_tokens":4}'
echo
echo "smoke ok"
