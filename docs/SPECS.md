# SPECS — simple-tools

## Overview

`simple-tools` is a collection of small Python CLIs exposed as subcommands under a single entrypoint. One install, one venv, one command surface — many tools.

Theme: small, focused, hand-built CLIs — built for fun, occasionally useful, never useless.

Invocation shape:
```
simple-tools <tool> [args...]
simple-tools --help            # lists all tools
simple-tools <tool> --help     # help for one tool
```

---

## Tooling Stack

| Concern | Choice |
|---|---|
| Package & project manager | `uv` |
| Python version | `>=3.12` |
| Virtual env | `.venv/` at repo root (gitignored) |
| CLI library | `typer` |
| Test runner | `pytest` (`uv run pytest`) |
| Type checker | `mypy` (run via `/pre-commit`) |

System dependencies (e.g. `ffmpeg`) are documented per-tool in this spec, not vendored.

---

## Repo Layout

```
simple-tools/
├── pyproject.toml
├── uv.lock
├── .venv/                          # gitignored
├── .python-version
├── .env.template
├── .gitignore
├── AGENTS.md
├── README.md
│
├── docs/
│   ├── SPECS.md                    # this file
│   ├── EP-XXXXX_*.md               # active execution plans
│   └── archived/                   # completed EPs
│
├── output/                         # default destination for tool artifacts (gitignored)
│   └── <tool_name>/                # each tool writes under its own subfolder
│
├── src/
│   └── simple_tools/
│       ├── __init__.py
│       ├── cli.py                  # root Typer app; registers each tool
│       └── tools/
│           ├── __init__.py
│           └── <tool_name>/        # one folder per tool
│               ├── __init__.py     # exposes the tool's Typer app/command
│               ├── cli.py          # CLI surface (flags, entrypoint)
│               └── *.py            # additional internal modules as needed
│
└── tests/
    └── tools/
        └── <tool_name>/
            └── test_*.py
```

A single `[project.scripts]` entry in `pyproject.toml` exposes the CLI:
```toml
[project.scripts]
simple-tools = "simple_tools.cli:app"
```

---

## Tool Conventions

Every tool subcommand must:

1. **Live in `src/simple_tools/tools/<tool_name>/`** as a package. The package's `__init__.py` exposes a Typer command or sub-app; `cli.py` defines the CLI surface; further internal modules may be added as the tool grows.
2. **Subcommand name is kebab-case** (e.g. `yt-mp3`); package directory is snake_case (`yt_mp3/`).
3. **Provide `--help`** listing all flags. The root `simple-tools --help` should list it automatically.
4. **Exit non-zero on failure** with a single-line error to stderr. No tracebacks unless `--debug` is passed.
5. **Print machine-friendly success output to stdout** (e.g. the path of a produced file). Progress and chatter go to stderr.
6. **Have at least one pytest test** covering the happy path, using `typer.testing.CliRunner` against the root app.
7. **Document any system dependency** in this SPECS.md tool catalog.
8. **Stay under the 800-line file cap** per the project's `/file-size-check` rule.

What tools must NOT do:
- No cross-tool shared `utils` module. If two tools need the same helper, copy it. Re-evaluate if a third tool needs it.
- No global config file. If a tool needs persistent config, it owns its own dotfile under `~/.config/simple-tools/<tool>/`.
- No network calls in tests.

Dependency policy:
- All Python deps go in the single root `pyproject.toml`.
- Add deps with `uv add <pkg>`. Keep the dep list tight; remove unused entries when a tool is deleted.

Output policy:
- Tools that produce artifacts (downloads, conversions, generated images, reports, etc.) write by default to `output/<tool_name>/` at the repo root.
- The `output/` directory is gitignored. Tools must create their own subfolder if it does not exist.
- Every such tool must accept an `--output`/`-o` flag to override the destination directory. The default value of that flag is `output/<tool_name>` resolved relative to the current working directory.
- Tools that do not produce file artifacts (e.g. pure stdout utilities) do not need an `--output` flag and do not write to `output/`.

---

## Tool Catalog

### 1. `yt-mp3` — YouTube audio downloader

**Status:** available

Download the audio track of a YouTube video as an MP3 file.

**CLI shape:**
```
simple-tools yt-mp3 <url> [--output DIR] [--bitrate KBPS] [--filename NAME]
```

| Flag | Default | Notes |
|---|---|---|
| `<url>` (positional) | required | YouTube video URL |
| `--output`, `-o` | `output/yt-mp3` | Output directory; created if missing |
| `--bitrate`, `-b` | `192` | MP3 bitrate in kbps (e.g. 128, 192, 320) |
| `--filename`, `-f` | video title (sanitized) | Override output filename (without extension) |

**Dependencies:**
- Python: `yt-dlp`
- System: `ffmpeg` (used by yt-dlp for audio extraction; user must install separately, e.g. `brew install ffmpeg`)

**Behavior:**
- Validates the URL resolves to a YouTube video before downloading.
- Streams progress to stderr; final output path printed to stdout on success.
- Refuses to overwrite an existing file (a `--force` flag may be added later if needed).

**Out of scope (v1):**
- Playlists, channels, batch URLs
- Output formats other than MP3
- ID3 tag enrichment beyond yt-dlp defaults

### 2. `play-music` — random MP3 player from a folder

**Status:** available

Discover MP3s under a folder, shuffle, and play them via ffplay. Default behavior loops forever (reshuffling between passes); Ctrl-C stops cleanly.

**CLI shape:**
```
simple-tools play-music <folder> [--once] [--no-recursive] [--debug]
```

| Flag | Default | Notes |
|---|---|---|
| `<folder>` (positional) | required | Directory to scan for `.mp3` files |
| `--once` | off | Play one shuffled pass and exit instead of looping |
| `--no-recursive` | off | Scan only the top level of the folder |
| `--debug` | off | Re-raise exceptions instead of one-line stderr error |

**Dependencies:**
- Python: stdlib only
- System: `ffplay` (ships with `ffmpeg`; `brew install ffmpeg`)

**Behavior:**
- Discovers `.mp3` files (case-insensitive); recurses by default. Empty folder or missing folder → exit `1`.
- Shuffles with `random.shuffle` and plays each track via `ffplay -nodisp -autoexit -loglevel quiet`.
- Prints `▶ <path>` to stdout per track; ffplay output is silenced.
- Ctrl-C exits `0` cleanly (no traceback unless `--debug`).
- Missing `ffplay` on PATH → exit `1` with install hint pointing at `brew install ffmpeg`.

**Out of scope (v1):**
- Audio formats other than MP3 (`.m4a` / `.flac` / `.ogg` deferred)
- Pause / skip / volume / interactive controls
- Playlist persistence between runs

---

## Development Setup

```bash
# one-time
uv sync                              # creates .venv, installs project + deps

# day-to-day
uv run simple-tools <tool> [args]    # run a tool
uv run pytest tests/ -v              # run all tests
```

Adding a new tool:
1. Create `src/simple_tools/tools/<tool_name>/` with `__init__.py` and `cli.py` defining a Typer command or sub-app.
2. Register it in `src/simple_tools/cli.py` (`app.add_typer(...)` or `@app.command(...)`).
3. Add tests in `tests/tools/<tool_name>/test_*.py`.
4. Add a new entry to the **Tool Catalog** section above.
5. `uv add <new-deps>` if the tool needs new packages.

---

## Open Questions

Tracked here until decided; remove when resolved.

- None currently.
