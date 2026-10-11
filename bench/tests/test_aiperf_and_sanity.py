from pathlib import Path

import pytest

from bench.aiperf import aiperf_command, cost_per_1m, parse_aiperf_json
from bench.configs.matrix import configs
from bench.sanity import decode_floor_ms, itl_beats_floor, littles_law_ok


def test_aiperf_command_includes_streaming() -> None:
    cmd = aiperf_command(
        {
            "model": "llama-8b-vllm-fp16",
            "concurrency": 32,
            "input_tokens": 512,
            "output_tokens": 256,
            "requests": 300,
            "warmup_requests": 30,
        },
        "http://127.0.0.1:8080",
    )
    assert cmd[0] == "aiperf"
    assert "--streaming" in cmd
    assert "32" in cmd


def test_parse_aiperf_json(tmp_path: Path) -> None:
    path = tmp_path / "raw.json"
    path.write_text(
        '{"time_to_first_token": {"p50": 12.5, "p95": 40}, '
        '"inter_token_latency": {"p50": 20}, '
        '"output_token_throughput": {"avg": 800}, '
        '"request_throughput": {"avg": 3}}',
        encoding="utf-8",
    )
    metrics = parse_aiperf_json(path)
    assert metrics["ttft_p50_ms"] == 12.5
    assert metrics["output_tokens_per_s"] == 800


def test_cost_and_floors() -> None:
    assert cost_per_1m(1000.0, 0.70) == pytest.approx(0.194444, rel=1e-3)
    assert decode_floor_ms("fp16") > 50
    assert itl_beats_floor("fp16", 1.0) is True
    assert itl_beats_floor("fp16", 80.0) is False
    assert littles_law_ok(32, 20.0, 1600.0) is True


def test_matrix_covers_spec() -> None:
    rows = configs()
    names = {row["name"] for row in rows}
    assert "vllm-fp16-c32-chat" in names
    assert "triton-fp8-c64-rag" in names
    assert len(rows) == 6 * 4 * 2
