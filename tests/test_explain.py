from __future__ import annotations

from ds_cheatsheet.explain import explain


def test_explain_simple_command() -> None:
    result = explain("ls -la /tmp")
    kinds = [t.kind for t in result.tokens]
    assert kinds[0] == "command"
    assert "flag" in kinds
    assert "value" in kinds


def test_explain_flags_and_values() -> None:
    result = explain("rg -t py 'TODO' src/")
    values = [t.value for t in result.tokens]
    assert "rg" in values
    assert "-t" in values
    assert "src/" in values


def test_explain_known_command_description() -> None:
    result = explain("git status")
    git_tok = next(t for t in result.tokens if t.value == "git")
    assert "version control" in git_tok.description.lower()


def test_explain_long_flag_with_equals() -> None:
    result = explain("docker run --gpus=all ubuntu")
    flag_tok = next(t for t in result.tokens if t.value == "--gpus")
    assert flag_tok.kind == "flag"
    val_tok = next(t for t in result.tokens if t.value == "all")
    assert val_tok.kind == "value"


def test_explain_detects_dangerous() -> None:
    result = explain("sudo rm -rf /")
    assert result.dangerous
    assert result.danger_reasons


def test_explain_empty_command() -> None:
    result = explain("")
    assert result.tokens == ()
    assert "empty" in " ".join(result.notes).lower()
