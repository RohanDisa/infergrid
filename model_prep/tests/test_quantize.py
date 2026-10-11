from pathlib import Path

from model_prep.quantize_awq import main as awq_main
from model_prep.quantize_fp8 import main as fp8_main


def test_awq_dry_run_writes_manifest(tmp_path: Path) -> None:
    out = tmp_path / "awq"
    awq_main(
        [
            "--model-dir",
            str(tmp_path / "src"),
            "--out",
            str(out),
            "--source-revision",
            "deadbeef",
            "--dry-run",
        ]
    )
    text = (out / "manifest.json").read_text(encoding="utf-8")
    assert "awq-int4" in text
    assert "ultrachat_200k" in text
    assert "deadbeef" in text


def test_fp8_dry_run_writes_manifest(tmp_path: Path) -> None:
    out = tmp_path / "fp8"
    fp8_main(["--model-dir", str(tmp_path / "src"), "--out", str(out), "--dry-run"])
    assert "fp8" in (out / "manifest.json").read_text(encoding="utf-8")
