from __future__ import annotations

from pathlib import Path

import pytest

from app.routing import RouteTable, RouteTableConfig, load_route_config

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def routes_path() -> Path:
    return FIXTURES / "routes.yaml"


@pytest.fixture()
def route_table(routes_path: Path) -> RouteTable:
    return RouteTable(load_route_config(routes_path))


@pytest.fixture()
def empty_config() -> RouteTableConfig:
    return RouteTableConfig()
