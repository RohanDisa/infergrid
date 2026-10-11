from __future__ import annotations

import random
from pathlib import Path

import pytest

from app.routing import (
    AliasRoute,
    ConcreteRoute,
    RouteStore,
    RouteTable,
    RouteTableConfig,
    UnknownModelError,
    WeightedTarget,
)


def test_resolve_concrete_route(route_table: RouteTable) -> None:
    resolution = route_table.resolve("llama-8b-vllm-fp16")
    assert resolution.route.backend == "vllm"
    assert resolution.route.url == "http://vllm-fp16:8000"
    assert resolution.via_alias is None


def test_unknown_model(route_table: RouteTable) -> None:
    with pytest.raises(UnknownModelError):
        route_table.resolve("does-not-exist")


def test_alias_is_deterministic_with_rng(route_table: RouteTable) -> None:
    left = route_table.resolve("llama-8b", rng=random.Random(0))
    right = route_table.resolve("llama-8b", rng=random.Random(0))
    assert left.route.name == right.route.name
    assert left.via_alias == "llama-8b"


def test_x_backend_forces_triton_on_alias(route_table: RouteTable) -> None:
    resolution = route_table.resolve("llama-8b", backend="triton", rng=random.Random(1))
    assert resolution.route.backend == "triton"
    assert resolution.route.name == "llama-8b-trtllm-fp8"


def test_x_backend_overrides_concrete_vllm_route(route_table: RouteTable) -> None:
    resolution = route_table.resolve("llama-8b-vllm-fp16", backend="triton")
    assert resolution.route.backend == "triton"


def test_listed_models_include_aliases(route_table: RouteTable) -> None:
    names = route_table.listed_models()
    assert "llama-8b" in names
    assert "llama-8b-vllm-fp16" in names


def test_alias_with_missing_target_rejected() -> None:
    config = RouteTableConfig(
        routes=[],
        aliases=[AliasRoute(name="x", weighted=[WeightedTarget(route="missing", weight=1)])],
    )
    with pytest.raises(ValueError, match="unknown route"):
        RouteTable(config)


def test_hot_reload_picks_up_new_file(tmp_path: Path) -> None:
    path = tmp_path / "routes.yaml"
    path.write_text(
        """
routes:
  - name: only-vllm
    backend: vllm
    url: http://vllm:8000
""",
        encoding="utf-8",
    )
    store = RouteStore(path)
    store.load()
    assert "only-vllm" in store.table().routes
    assert store.reload_if_changed() is False

    path.write_text(
        """
routes:
  - name: only-triton
    backend: triton
    url: http://triton:8000
""",
        encoding="utf-8",
    )
    assert store.reload_if_changed() is True
    assert "only-triton" in store.table().routes
    assert "only-vllm" not in store.table().routes


def test_zero_weight_alias_rejected() -> None:
    with pytest.raises(ValueError):
        AliasRoute(name="x", weighted=[WeightedTarget(route="a", weight=0)])


def test_concrete_route_defaults() -> None:
    route = ConcreteRoute(name="m", backend="mock", url="http://mock:8000")
    assert route.openai_compatible is True
