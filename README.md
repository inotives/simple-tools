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

> **For AI agents:** every tool exposes its full flag surface via `--help`. Run `uv run simple-tools <tool> --help` before invoking a tool to discover its arguments, defaults, and behavior. The per-tool sections below mirror that output.

Artifacts (downloads, conversions, generated files) are written by default to `output/<tool>/` at the repo root.

## Tools

| Command | Description | Status |
|---|---|---|
| `yt-mp3` | Download a YouTube video's audio as MP3 | available |

See [`docs/SPECS.md`](docs/SPECS.md) for full per-tool specs.

### `yt-mp3`

Download a YouTube video's audio as an MP3. Requires `ffmpeg` on PATH (e.g. `brew install ffmpeg`).

**Usage**

```
simple-tools yt-mp3 [OPTIONS] URL
```

**Arguments**

| Name | Required | Description |
|---|---|---|
| `URL` | yes | YouTube video URL to extract audio from. Playlists and channel URLs are not supported. |

**Options**

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--output` | `-o` | path | `output/yt-mp3` | Directory to write the MP3 into. Created if missing. Resolved relative to CWD. |
| `--bitrate` | `-b` | int | `192` | MP3 bitrate in kbps. Common values: 128 (compact), 192 (balanced), 320 (highest standard MP3 quality). |
| `--filename` | `-f` | str | video title (sanitized) | Output filename without extension. The `.mp3` extension is added automatically. Path separators are stripped. |
| `--debug` |  | flag | off | On failure, show the full Python traceback instead of a single-line error message. |
| `--help` |  | flag |  | Show full help and exit. |

**Behavior**

- On success: prints the absolute path of the produced MP3 to stdout (one line). Progress goes to stderr.
- On failure: exits `1` with a one-line stderr message (use `--debug` for full traceback). Missing required argument exits `2`.
- Refuses to overwrite an existing file at the target path.

**Examples**

```bash
# default: writes to ./output/yt-mp3/<sanitized-title>.mp3
uv run simple-tools yt-mp3 "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# custom filename + bitrate + output dir
uv run simple-tools yt-mp3 \
  "https://www.youtube.com/watch?v=jNQXAC9IVRw" \
  --filename me-at-the-zoo \
  --bitrate 320 \
  --output ~/Music/clips
```

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
