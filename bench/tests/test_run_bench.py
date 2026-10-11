from pathlib import Path

from bench.run_bench import main


def test_run_bench_dry_run_writes_command(tmp_path: Path) -> None:
    config = tmp_path / "cfg.yaml"
    config.write_text(
        "\n".join(
            [
                "name: unit-placeholder",
                "backend: vllm",
                "precision: fp16",
                "concurrency: 1",
                "input_tokens: 16",
                "output_tokens: 8",
                "model: llama-8b-vllm-fp16",
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "results"
    main(
        [
            "--config",
            str(config),
            "--out-dir",
            str(out),
            "--commit",
            "test",
        ]
    )
    text = (out / "unit-placeholder.json").read_text(encoding="utf-8")
    assert "not_run" in text
    assert "aiperf" in text
    assert "dry-run" in text
