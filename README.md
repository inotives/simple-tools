# simple-tools

A collection of small Python CLIs exposed as subcommands under a single entrypoint. One install, one venv, many tools.

Built for fun, occasionally useful, never useless.

## Install

Requires [`uv`](https://github.com/astral-sh/uv) and Python `>=3.12`.

```bash
git clone <repo-url> simple-tools
cd simple-tools
uv sync
```

Some tools have system-level dependencies (e.g. `ffmpeg`). Check the per-tool entry in [`docs/SPECS.md`](docs/SPECS.md#tool-catalog).

## Usage

```bash
uv run simple-tools --help               # list all tools
uv run simple-tools <tool> --help        # help for a specific tool
uv run simple-tools <tool> [args...]     # run a tool
```

Artifacts (downloads, conversions, generated files) are written by default to `output/<tool>/` at the repo root.

## Tools

| Command | Description | Status |
|---|---|---|
| `yt-mp3` | Download a YouTube video's audio as MP3 | planned |

See [`docs/SPECS.md`](docs/SPECS.md) for full per-tool specs.

## Project Layout

```
simple-tools/
├── docs/                       # SPECS + execution plans
├── output/                     # tool artifacts (gitignored)
├── src/simple_tools/
│   ├── cli.py                  # root Typer app
│   └── tools/<tool_name>/      # one package per tool
└── tests/
```

## Development

```bash
uv run pytest tests/ -v          # run all tests
uv run simple-tools <tool> ...   # run a tool from the workspace venv
```

Project conventions, slash commands, and contribution workflow are documented in [`AGENTS.md`](AGENTS.md).

## License

MIT — see [`LICENSE`](LICENSE).
