import sys
from pathlib import Path
from typing import Annotated

import typer

from simple_tools.tools.prompt_optimizer.optimizer import (
    ProviderError,
    load_dotenv,
    optimize,
)


def prompt_optimizer(
    text: Annotated[
        str | None,
        typer.Argument(
            help=(
                "Short idea to expand into a structured agent prompt. "
                "Required unless --stdin is passed."
            ),
            show_default=False,
        ),
    ] = None,
    stdin: Annotated[
        bool,
        typer.Option(
            "--stdin",
            help="Read the input idea from stdin instead of the positional argument.",
        ),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Write the optimized prompt to this file instead of stdout. "
                "Refuses to overwrite an existing file."
            ),
            show_default=False,
        ),
    ] = None,
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            help=(
                "LLM provider. 'auto' tries Groq then NVIDIA NIM. "
                "'groq' or 'nvidia' force a single provider."
            ),
        ),
    ] = "auto",
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            help="Override the provider's default model name.",
            show_default=False,
        ),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="On failure, show the full Python traceback.",
        ),
    ] = False,
) -> None:
    """Turn a short idea into a structured prompt optimized for agent context.

    Sends the idea to a free LLM (Groq, then NVIDIA NIM as fallback) wrapped in
    a meta-prompt that asks for a Goal/Context/Task/Constraints/Success
    Criteria/Output Format structure. Prints the result to stdout (or writes
    it to --output).
    """
    if provider not in ("auto", "groq", "nvidia"):
        typer.echo(
            f"prompt-optimizer: unknown --provider {provider!r} "
            "(expected: auto, groq, nvidia)",
            err=True,
        )
        raise typer.Exit(code=2)

    if stdin:
        if text is not None:
            typer.echo(
                "prompt-optimizer: pass either <text> or --stdin, not both",
                err=True,
            )
            raise typer.Exit(code=2)
        idea = sys.stdin.read()
    else:
        if text is None:
            typer.echo(
                "prompt-optimizer: missing input. Pass <text> or use --stdin.",
                err=True,
            )
            raise typer.Exit(code=2)
        idea = text

    if not idea.strip():
        typer.echo("prompt-optimizer: input is empty", err=True)
        raise typer.Exit(code=1)

    if output is not None and output.exists():
        typer.echo(
            f"prompt-optimizer: refusing to overwrite existing file: {output}",
            err=True,
        )
        raise typer.Exit(code=1)

    load_dotenv()

    try:
        result = optimize(idea, provider, model)
    except ProviderError as exc:
        if debug:
            raise
        typer.echo(f"prompt-optimizer: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        if debug:
            raise
        typer.echo(f"prompt-optimizer: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"prompt-optimizer: provider={result.provider}", err=True)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.prompt + "\n", encoding="utf-8")
        typer.echo(str(output.resolve()))
    else:
        typer.echo(result.prompt)
