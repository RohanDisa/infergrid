# Builder image: same NGC tag we serve with so engines cannot drift.
# Tag is pinned in VERSIONS.md.
ARG TRITON_TAG=26.07-trtllm-python-py3
FROM nvcr.io/nvidia/tritonserver:${TRITON_TAG}

WORKDIR /workspace
COPY build_engine.sh /workspace/build_engine.sh
RUN chmod +x /workspace/build_engine.sh
ENTRYPOINT ["/workspace/build_engine.sh"]
