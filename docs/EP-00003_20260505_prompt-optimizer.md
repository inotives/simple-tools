# EP-00003 — prompt-optimizer: turn a one-line idea into a structured agent prompt

> **Status:** IN PROGRESS
> **Locked decisions (2026-05-05):** name is `prompt-optimizer`; provider order is Groq → NVIDIA NIM; output format follows superpowers principles (concise, trigger-driven, progressive disclosure) shaped as an agent prompt with Goal / Context / Task / Constraints / Success Criteria / Output Format sections.

## Problem / Pain Points

- Writing a good prompt for an agent (Claude / GPT / etc.) is tedious. We typically scribble a one-liner ("build me a CLI that converts CSV to parquet") and the agent then asks five clarifying questions or invents missing context.
- We want a CLI that takes a short idea and emits a fully structured prompt suitable for handing straight to an agent — sized for the agent's context, with explicit goal, constraints, and success criteria.
- Constraints from `docs/SPECS.md`:
  - One subcommand on the existing Typer entrypoint, package under `src/simple_tools/tools/<name>/`.
  - Stdout discipline: print the optimized prompt to stdout. Errors and progress go to stderr.
  - Per-tool naming: kebab-case command (`prompt-optimizer`), snake_case package (`prompt_optimizer`).
  - No new shared "common" module across tools. Stays self-contained.
  - No network calls in tests (all HTTP must be mocked).

## Suggested Solution

### Tool name

`prompt-optimizer` — locked.

### LLM backend

**Choice: Groq primary, NVIDIA NIM fallback.** Both are free-tier OpenAI-compatible chat-completions APIs:
- Groq: `https://api.groq.com/openai/v1/chat/completions`, default model `llama-3.3-70b-versatile`. Reads `GROQ_API_KEY` from env.
- NVIDIA NIM: `https://integrate.api.nvidia.com/v1/chat/completions`, default model `meta/llama-3.3-70b-instruct`. Reads `NVIDIA_NIM_API_KEY` (alias `NVIDIA_API_KEY`) from env.

Fallback rule: if Groq returns a non-2xx response, times out, or its API key is unset, fall through to NVIDIA NIM. If both fail, exit `1` with a stderr message naming each provider's failure.

No new Python deps — use stdlib `urllib.request` + `json`. Both endpoints are simple POSTs.

### Output format

Inspired by `/Users/toni.lim/Workspace/superpowers` writing-skills guidance:
- Concise — assume the receiving agent is smart; only add context it doesn't already have.
- Trigger-driven — make the goal and success criteria scannable.
- Progressive disclosure — short overview first, details after.

The optimized prompt is plain markdown, ready to paste into an agent:

```markdown
# {Title — short, action-oriented}

## Goal
{One-sentence outcome}

## Context
{Background only the agent doesn't already know}

## Task
{Concrete steps or instructions}

## Constraints
- {Hard rules / what to avoid}

## Success Criteria
- {Verifiable outcome 1}
- {Verifiable outcome 2}

## Output Format
{What the agent should return}
```

The meta-prompt sent to the LLM tells it to fill exactly these sections, keep the whole thing under ~400 words, omit boilerplate, and not invent details the user didn't supply (use `{TODO: …}` placeholders if a section can't be reasonably inferred).

### CLI shape

```
simple-tools prompt-optimizer <text> [--output FILE] [--stdin] [--provider auto|groq|nvidia] [--model NAME] [--debug]
```

| Flag | Default | Notes |
|---|---|---|
| `<text>` (positional) | required unless `--stdin` | The simple idea to expand into a prompt. |
| `--stdin` | off | Read the input idea from stdin instead of the positional arg. |
| `--output`, `-o` | none | Write the optimized prompt to this file. Refuses to overwrite. If omitted, prints to stdout. |
| `--provider` | `auto` | `auto` = try Groq then NVIDIA. `groq` / `nvidia` force one provider. |
| `--model` | provider default | Override the model name. |
| `--debug` | off | Re-raise exceptions with full traceback. |

Behavior:
- Exit `1` with a clear stderr message if no API keys are set for any allowed provider.
- Exit `1` if both providers fail in `auto` mode.
- Print the optimized prompt to stdout (or write to `--output`). Progress messages (e.g. `using provider: groq`) go to stderr.

### Tool layout

```
src/simple_tools/tools/prompt_optimizer/
├── __init__.py       # re-exports the Typer command
├── cli.py            # CLI surface (flags, IO, exit codes)
└── optimizer.py      # provider clients + orchestration (testable unit)
```

`optimizer.py` exposes:
- `optimize(idea: str, provider: str, model: str | None) -> OptimizeResult` — orchestrates provider order; returns the optimized prompt + which provider answered.
- `call_groq(idea: str, model: str | None) -> str` and `call_nvidia(idea: str, model: str | None) -> str` — thin OpenAI-compatible POSTs.
- `META_PROMPT` constant — the system prompt that defines the output structure.
- `class ProviderError(RuntimeError)` — raised on HTTP / parse failure with provider name attached.

### Tests

`tests/tools/prompt_optimizer/`:
- `test_optimizer.py` — unit tests for the provider clients with `urllib.request.urlopen` patched. Cover: happy path returns text; non-200 raises `ProviderError`; missing API key raises `ProviderError`; `optimize()` falls through Groq → NVIDIA on first failure; `optimize()` raises when both fail.
- `test_cli.py` — `CliRunner` with `optimize` patched. Verify:
  - Happy path prints the optimized prompt to stdout, exit `0`.
  - `--output` writes to the file and refuses to overwrite.
  - `--stdin` reads from stdin.
  - Provider-failure path exits `1` with stderr message, no traceback unless `--debug`.

## Phases

1. **Skeleton + meta-prompt** → verify: package imports cleanly, `simple-tools prompt-optimizer --help` works.
2. **Provider clients** → verify: unit tests for Groq + NVIDIA pass with mocked `urlopen`.
3. **Orchestrator + CLI** → verify: CLI tests cover stdout/file/stdin/error paths.
4. **Docs** → update SPECS, README, AGENTS.md, .env.template.
5. **Manual smoke** → run against a real GROQ_API_KEY (user-driven, outside CI).
