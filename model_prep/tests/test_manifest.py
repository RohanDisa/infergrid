from pathlib import Path

import pytest

from model_prep.manifest import build, read, validate, write


def test_build_and_roundtrip(tmp_path: Path) -> None:
    row = build(
        artifact="fp16-hf",
        source_repo="Qwen/Qwen2.5-7B-Instruct",
        source_revision="abc123",
        tool="huggingface-cli",
        tool_version="1.0",
        precision="fp16",
        flags={"max_model_len": 4096},
    )
    path = tmp_path / "manifest.json"
    write(path, row)
    loaded = read(path)
    assert loaded["artifact"] == "fp16-hf"
    assert loaded["flags"]["max_model_len"] == 4096


def test_validate_rejects_incomplete() -> None:
    with pytest.raises(ValueError, match="missing"):
        validate({"artifact": "x"})
