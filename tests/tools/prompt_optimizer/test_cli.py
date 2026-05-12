from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from simple_tools.cli import app
from simple_tools.tools.prompt_optimizer import optimizer

runner = CliRunner()


def _ok(result_text: str = "# T\n\n## Goal\nx", provider: str = "groq"):  # type: ignore[no-untyped-def]
    return optimizer.OptimizeResult(prompt=result_text, provider=provider)


def test_happy_path_prints_to_stdout() -> None:
    with patch(
        "simple_tools.tools.prompt_optimizer.cli.optimize",
        return_value=_ok("OPTIMIZED"),
    ):
        result = runner.invoke(app, ["prompt-optimizer", "do a thing"])
    assert result.exit_code == 0
    assert "OPTIMIZED" in result.stdout


def test_writes_to_output_file(tmp_path: Path) -> None:
    out = tmp_path / "out.md"
    with patch(
        "simple_tools.tools.prompt_optimizer.cli.optimize",
        return_value=_ok("FILE_BODY"),
    ):
        result = runner.invoke(app, ["prompt-optimizer", "idea", "-o", str(out)])
    assert result.exit_code == 0, result.stdout
    assert out.read_text(encoding="utf-8").strip() == "FILE_BODY"
    assert str(out.resolve()) in result.stdout


def test_refuses_to_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "out.md"
    out.write_text("existing")
    with patch(
        "simple_tools.tools.prompt_optimizer.cli.optimize",
        return_value=_ok(),
    ) as m:
        result = runner.invoke(app, ["prompt-optimizer", "idea", "-o", str(out)])
    assert result.exit_code == 1
    m.assert_not_called()
    assert out.read_text() == "existing"


def test_missing_input_exits_2() -> None:
    result = runner.invoke(app, ["prompt-optimizer"])
    assert result.exit_code == 2


def test_stdin_and_arg_conflict_exits_2() -> None:
    result = runner.invoke(app, ["prompt-optimizer", "x", "--stdin"], input="y\n")
    assert result.exit_code == 2


def test_stdin_input_is_used() -> None:
    with patch(
        "simple_tools.tools.prompt_optimizer.cli.optimize",
        return_value=_ok("STDIN_OK"),
    ) as m:
        result = runner.invoke(
            app, ["prompt-optimizer", "--stdin"], input="hello idea\n"
        )
    assert result.exit_code == 0
    assert "STDIN_OK" in result.stdout
    assert m.call_args.args[0].strip() == "hello idea"


def test_empty_input_exits_1() -> None:
    result = runner.invoke(app, ["prompt-optimizer", "   "])
    assert result.exit_code == 1


def test_unknown_provider_exits_2() -> None:
    result = runner.invoke(
        app, ["prompt-optimizer", "idea", "--provider", "openai"]
    )
    assert result.exit_code == 2


def test_provider_failure_exits_1_no_traceback() -> None:
    with patch(
        "simple_tools.tools.prompt_optimizer.cli.optimize",
        side_effect=optimizer.ProviderError("all", "groq: down; nvidia: down"),
    ):
        result = runner.invoke(app, ["prompt-optimizer", "idea"])
    assert result.exit_code == 1
    assert "Traceback" not in result.stdout
    assert "groq" in result.stdout or "groq" in (result.stderr or "")


def test_debug_reraises() -> None:
    with patch(
        "simple_tools.tools.prompt_optimizer.cli.optimize",
        side_effect=optimizer.ProviderError("all", "boom"),
    ):
        result = runner.invoke(
            app, ["prompt-optimizer", "idea", "--debug"]
        )
    assert result.exit_code != 0
    assert isinstance(result.exception, optimizer.ProviderError)
