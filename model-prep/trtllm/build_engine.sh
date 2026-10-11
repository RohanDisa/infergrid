#!/usr/bin/env bash
# Build a TensorRT-LLM engine on the same GPU architecture it will serve on (L4).
# Run inside nvcr.io/nvidia/tritonserver:26.07-trtllm-python-py3 (see VERSIONS.md).
set -euo pipefail

HF_DIR="${HF_DIR:?set HF_DIR to the Hugging Face checkpoint}"
OUT_DIR="${OUT_DIR:?set OUT_DIR}"
DTYPE="${DTYPE:-float16}"
QFORMAT="${QFORMAT:-}"   # empty or fp8
MAX_BATCH="${MAX_BATCH:-64}"
MAX_INPUT_LEN="${MAX_INPUT_LEN:-3072}"
MAX_SEQ_LEN="${MAX_SEQ_LEN:-4096}"

CKPT="$OUT_DIR/ckpt"
ENGINE="$OUT_DIR/engine"
mkdir -p "$CKPT" "$ENGINE"

if [[ "$QFORMAT" == "fp8" ]]; then
  python quantize.py \
    --model_dir "$HF_DIR" \
    --output_dir "$CKPT" \
    --qformat fp8 \
    --kv_cache_dtype fp8
else
  python convert_checkpoint.py \
    --model_dir "$HF_DIR" \
    --output_dir "$CKPT" \
    --dtype "$DTYPE"
fi

trtllm-build \
  --checkpoint_dir "$CKPT" \
  --output_dir "$ENGINE" \
  --gemm_plugin auto \
  --max_batch_size "$MAX_BATCH" \
  --max_input_len "$MAX_INPUT_LEN" \
  --max_seq_len "$MAX_SEQ_LEN" \
  --paged_kv_cache enable

echo "engine written to $ENGINE"
echo "Confirm flags against the TRT-LLM $QFORMAT docs for the image in VERSIONS.md before a real build."
