"""Phase 8 sanity checks. Fail a result that beats the L4 memory-bandwidth floor."""

from __future__ import annotations

# L4 ~300 GB/s. Weight sizes for 8B.
L4_BANDWIDTH_GBS = 300.0
WEIGHT_GB = {"fp16": 16.0, "fp8": 8.0, "awq": 5.0, "awq-int4": 5.0, "int4": 5.0}


def decode_floor_ms(precision: str, bandwidth_gbs: float = L4_BANDWIDTH_GBS) -> float:
    key = precision.lower()
    if key not in WEIGHT_GB:
        raise KeyError(precision)
    return (WEIGHT_GB[key] / bandwidth_gbs) * 1000.0


def itl_beats_floor(precision: str, itl_p50_ms: float | None) -> bool:
    if itl_p50_ms is None:
        return False
    return itl_p50_ms < decode_floor_ms(precision) * 0.85


def littles_law_ok(
    concurrency: int,
    itl_p50_ms: float | None,
    output_tokens_per_s: float | None,
    *,
    slack: float = 2.5,
) -> bool:
    if not itl_p50_ms or not output_tokens_per_s:
        return True
    expected = concurrency / (itl_p50_ms / 1000.0)
    return abs(expected - output_tokens_per_s) / expected <= slack
