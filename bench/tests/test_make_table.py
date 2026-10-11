from bench.make_table import median_by_config, render


def test_empty_table_has_placeholder() -> None:
    text = render([])
    assert "no results yet" in text
    assert "TTFT p50/p95" in text


def test_median_across_repeats() -> None:
    rows = [
        {
            "backend": "vllm",
            "precision": "fp16",
            "concurrency": 32,
            "workload": "chat",
            "ttft_p50_ms": 10,
        },
        {
            "backend": "vllm",
            "precision": "fp16",
            "concurrency": 32,
            "workload": "chat",
            "ttft_p50_ms": 30,
        },
        {
            "backend": "vllm",
            "precision": "fp16",
            "concurrency": 32,
            "workload": "chat",
            "ttft_p50_ms": 20,
        },
    ]
    merged = median_by_config(rows)
    assert merged[0]["ttft_p50_ms"] == 20.0
