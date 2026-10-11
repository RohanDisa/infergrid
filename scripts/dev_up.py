#!/usr/bin/env python3
"""Run mock-backend + gateway on the host. No Docker, no Kind."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOCK_PORT = int(os.environ.get("MOCK_PORT", "8000"))
GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8080"))


def main() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "gateway"), str(ROOT / "mock-backend"), env.get("PYTHONPATH", "")]
    )
    env["INFERGRID_ROUTES_PATH"] = str(ROOT / "gateway" / "routes.local.yaml")
    env.setdefault("INFERGRID_RELOAD_INTERVAL_SECONDS", "0")

    mock = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "mock_app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(MOCK_PORT),
        ],
        cwd=str(ROOT / "mock-backend"),
        env=env,
    )
    gateway = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(GATEWAY_PORT),
        ],
        cwd=str(ROOT / "gateway"),
        env=env,
    )
    print(f"mock     http://127.0.0.1:{MOCK_PORT}/health")
    print(f"gateway  http://127.0.0.1:{GATEWAY_PORT}/v1/models")
    print("Ctrl+C to stop")

    def _stop(_signum: int, _frame: object) -> None:
        for proc in (gateway, mock):
            if proc.poll() is None:
                proc.terminate()

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    try:
        while gateway.poll() is None and mock.poll() is None:
            time.sleep(0.4)
    finally:
        _stop(0, None)
        gateway.wait(timeout=5)
        mock.wait(timeout=5)


if __name__ == "__main__":
    main()
