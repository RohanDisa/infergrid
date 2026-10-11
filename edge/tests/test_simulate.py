from edge.simulate import tradeoffs, vllm_args


def test_simulate_uses_thirty_percent_memory() -> None:
    args = vllm_args()
    assert "--gpu-memory-utilization" in args
    assert "0.3" in args
    assert "awq" in args
    assert "privacy" in tradeoffs()
