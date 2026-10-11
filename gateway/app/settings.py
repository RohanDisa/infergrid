from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INFERGRID_", extra="ignore")

    routes_path: Path = Field(default=Path("/etc/infergrid/routes.yaml"))
    reload_interval_seconds: float = 5.0
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 300.0
    write_timeout_seconds: float = 30.0
    pool_timeout_seconds: float = 5.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    retry_connect: bool = True
    ready_check_timeout_seconds: float = 2.0


def load_settings() -> Settings:
    return Settings()
