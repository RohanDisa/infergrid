from pathlib import Path

from model_prep.trtllm.fill_template import fill_tree, load_values, render


def test_render_replaces_placeholders() -> None:
    text = render("batch=${N} mode=${MODE}", {"N": "64", "MODE": "true"})
    assert text == "batch=64 mode=true"


def test_render_strict_missing() -> None:
    try:
        render("${MISSING}", {})
    except KeyError as exc:
        assert "MISSING" in str(exc)
    else:
        raise AssertionError("expected KeyError")


def test_fill_tree_from_repo(tmp_path: Path) -> None:
    src = Path("model-prep/trtllm/repo")
    dest = tmp_path / "out"
    values = load_values(Path("model-prep/trtllm/values-fp16.yaml"), [])
    written = fill_tree(src, dest, values)
    assert written
    engine = (dest / "tensorrt_llm" / "config.pbtxt").read_text(encoding="utf-8")
    assert "${" not in engine
    assert "inflight_fused_batching" in engine
    assert "0.9" in engine
