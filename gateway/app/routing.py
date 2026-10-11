from __future__ import annotations

import random
import threading
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

BackendName = Literal["vllm", "triton", "mock"]


class ConcreteRoute(BaseModel):
    name: str
    backend: BackendName
    url: str
    upstream_model: str | None = None
    openai_compatible: bool = True
    deployment: str | None = None


class WeightedTarget(BaseModel):
    route: str
    weight: int = Field(ge=0)


class AliasRoute(BaseModel):
    name: str
    weighted: list[WeightedTarget]

    @model_validator(mode="after")
    def weights_must_sum_positive(self) -> AliasRoute:
        if sum(item.weight for item in self.weighted) <= 0:
            raise ValueError(f"alias {self.name} has no positive weights")
        return self


class RouteTableConfig(BaseModel):
    routes: list[ConcreteRoute] = Field(default_factory=list)
    aliases: list[AliasRoute] = Field(default_factory=list)


class RouteResolution(BaseModel):
    route: ConcreteRoute
    requested_model: str
    via_alias: str | None = None


class UnknownModelError(KeyError):
    pass


class RouteTable:
    """In-memory route table. Safe to swap atomically via replace()."""

    def __init__(self, config: RouteTableConfig) -> None:
        self._config = config
        self._routes = {route.name: route for route in config.routes}
        self._aliases = {alias.name: alias for alias in config.aliases}
        for alias in config.aliases:
            for target in alias.weighted:
                if target.route not in self._routes:
                    raise ValueError(f"alias {alias.name} references unknown route {target.route}")

    @property
    def routes(self) -> dict[str, ConcreteRoute]:
        return self._routes

    @property
    def aliases(self) -> dict[str, AliasRoute]:
        return self._aliases

    def listed_models(self) -> list[str]:
        names = list(self._routes.keys()) + list(self._aliases.keys())
        return sorted(set(names))

    def resolve(
        self,
        model: str,
        *,
        backend: str | None = None,
        rng: random.Random | None = None,
    ) -> RouteResolution:
        picker = rng if rng is not None else random.Random()

        if model in self._aliases:
            chosen = self._pick_weighted(self._aliases[model], backend=backend, rng=picker)
            return RouteResolution(route=chosen, requested_model=model, via_alias=model)

        if model in self._routes:
            route = self._routes[model]
            if backend and route.backend != backend:
                forced = self._first_backend(backend)
                return RouteResolution(route=forced, requested_model=model)
            return RouteResolution(route=route, requested_model=model)

        if backend:
            return RouteResolution(route=self._first_backend(backend), requested_model=model)

        raise UnknownModelError(model)

    def _pick_weighted(
        self,
        alias: AliasRoute,
        *,
        backend: str | None,
        rng: random.Random,
    ) -> ConcreteRoute:
        targets = alias.weighted
        if backend:
            filtered = [item for item in targets if self._routes[item.route].backend == backend]
            if filtered:
                targets = filtered
            else:
                return self._first_backend(backend)
        names = [item.route for item in targets]
        weights = [item.weight for item in targets]
        chosen = rng.choices(names, weights=weights, k=1)[0]
        return self._routes[chosen]

    def _first_backend(self, backend: str) -> ConcreteRoute:
        for route in self._routes.values():
            if route.backend == backend:
                return route
        raise UnknownModelError(f"no route for backend={backend}")


class RouteStore:
    """Hot-reloadable route table backed by a YAML file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._mtime_ns: int | None = None
        self._table = RouteTable(RouteTableConfig())

    @property
    def path(self) -> Path:
        return self._path

    def table(self) -> RouteTable:
        with self._lock:
            return self._table

    def load(self) -> RouteTable:
        config = load_route_config(self._path)
        table = RouteTable(config)
        mtime = self._path.stat().st_mtime_ns
        with self._lock:
            self._table = table
            self._mtime_ns = mtime
        return table

    def reload_if_changed(self) -> bool:
        if not self._path.exists():
            return False
        mtime = self._path.stat().st_mtime_ns
        with self._lock:
            if self._mtime_ns == mtime:
                return False
        self.load()
        return True


def load_route_config(path: Path) -> RouteTableConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return RouteTableConfig.model_validate(raw)
