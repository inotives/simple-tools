import typer

from simple_tools.tools.play_music import play_music
from simple_tools.tools.prompt_optimizer import prompt_optimizer
from simple_tools.tools.yt_mp3 import yt_mp3

app = typer.Typer(
    name="simple-tools",
    help="A collection of small Python CLIs exposed as subcommands.",
    no_args_is_help=True,
    add_completion=False,
)

@app.callback()
def _root() -> None:
    """A collection of small Python CLIs exposed as subcommands."""


app.command("yt-mp3")(yt_mp3)
app.command("play-music")(play_music)
app.command("prompt-optimizer")(prompt_optimizer)


if __name__ == "__main__":
    app()
