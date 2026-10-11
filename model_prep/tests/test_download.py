from pathlib import Path

from model_prep.download import main


def test_download_dry_run(tmp_path: Path) -> None:
    out = tmp_path / "weights"
    main(["--repo", "Qwen/Qwen2.5-7B-Instruct", "--out", str(out), "--dry-run"])
    text = (out / "manifest.json").read_text(encoding="utf-8")
    assert "Qwen/Qwen2.5-7B-Instruct" in text
    assert "fp16-hf" in text
