import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"

REQUEST_TIMEOUT_SECONDS = 60


def load_dotenv(start: Path | None = None) -> Path | None:
    """Walk up from `start` (or CWD) looking for a .env file; load its values.

    Existing environment variables are NOT overridden — explicit env wins.
    Returns the path that was loaded, or None if no .env was found.

    Format: KEY=VALUE per line. '#' starts a comment. Surrounding single or
    double quotes on VALUE are stripped. Blank lines are ignored.
    """
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        env_file = candidate / ".env"
        if env_file.is_file():
            break
    else:
        return None

    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
    return env_file

META_PROMPT = """\
You are a prompt engineer. Rewrite the user's short idea into a structured \
prompt that an AI coding/agent will receive as its task brief.

Output ONLY the rewritten prompt as plain GitHub-flavored markdown. No \
preamble, no commentary, no code fences around the whole thing.

Use exactly these sections, in this order:

# {Short, action-oriented title — 6 words or fewer}

## Goal
{One sentence stating the desired outcome.}

## Context
{Background the agent likely does not already know. Skip facts a competent \
agent would already have. If the user did not supply enough context, write \
"{TODO: ...}" placeholders rather than inventing details.}

## Task
{Concrete steps or instructions. Numbered list if there are multiple steps.}

## Constraints
- {Hard rules, what to avoid, scope limits.}

## Success Criteria
- {Verifiable outcome the agent can check itself against.}
- {Add 1-3 more if relevant.}

## Output Format
{What the agent should return — code, a PR, a markdown report, etc.}

Rules:
- Keep the whole prompt under 400 words.
- Be concise. Assume the receiving agent is competent.
- Do not invent specifics (libraries, file names, metrics) the user did not mention; use {TODO} placeholders instead.
- No emojis. No marketing language.\
"""


@dataclass(frozen=True)
class OptimizeResult:
    prompt: str
    provider: str


class ProviderError(RuntimeError):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider


def _post_chat(
    url: str,
    api_key: str,
    model: str,
    idea: str,
    provider: str,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": META_PROMPT},
            {"role": "user", "content": idea},
        ],
        "temperature": 0.4,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "simple-tools-prompt-optimizer/0.1 (+https://github.com/inotives/simple-tools)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise ProviderError(provider, f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(provider, f"network error: {exc.reason}") from exc

    try:
        parsed: dict[str, Any] = json.loads(body)
        choices = parsed["choices"]
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        raise ProviderError(provider, f"unexpected response shape: {exc}") from exc

    if not isinstance(content, str) or not content.strip():
        raise ProviderError(provider, "empty completion content")
    return content.strip()


def call_groq(idea: str, model: str | None) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ProviderError("groq", "GROQ_API_KEY is not set")
    return _post_chat(GROQ_URL, api_key, model or GROQ_DEFAULT_MODEL, idea, "groq")


def call_nvidia(idea: str, model: str | None) -> str:
    api_key = os.environ.get("NVIDIA_NIM_API_KEY") or os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise ProviderError("nvidia", "NVIDIA_NIM_API_KEY is not set")
    return _post_chat(NVIDIA_URL, api_key, model or NVIDIA_DEFAULT_MODEL, idea, "nvidia")


def optimize(idea: str, provider: str, model: str | None) -> OptimizeResult:
    """Optimize the idea via the chosen provider, with auto-fallback.

    provider:
      - "auto"   → try groq, then nvidia.
      - "groq"   → groq only.
      - "nvidia" → nvidia only.
    """
    idea = idea.strip()
    if not idea:
        raise ValueError("idea is empty")

    attempts: list[tuple[str, Any]] = []
    if provider in ("auto", "groq"):
        attempts.append(("groq", call_groq))
    if provider in ("auto", "nvidia"):
        attempts.append(("nvidia", call_nvidia))
    if not attempts:
        raise ValueError(f"unknown provider: {provider!r}")

    errors: list[str] = []
    for name, fn in attempts:
        try:
            text = fn(idea, model)
        except ProviderError as exc:
            errors.append(str(exc))
            continue
        return OptimizeResult(prompt=text, provider=name)

    raise ProviderError("all", "; ".join(errors))
