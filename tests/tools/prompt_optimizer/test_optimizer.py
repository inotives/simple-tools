import io
import json
import os
import urllib.error
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from simple_tools.tools.prompt_optimizer import optimizer


def _fake_response(payload: dict[str, Any]) -> Any:
    body = json.dumps(payload).encode("utf-8")

    class _Resp:
        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def read(self) -> bytes:
            return body

    return _Resp()


OK_PAYLOAD = {
    "choices": [{"message": {"content": "# Title\n\n## Goal\nx\n"}}]
}


def test_call_groq_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    with patch("urllib.request.urlopen", return_value=_fake_response(OK_PAYLOAD)) as m:
        out = optimizer.call_groq("idea", None)
    assert out.startswith("# Title")
    req = m.call_args.args[0]
    assert req.full_url == optimizer.GROQ_URL
    assert req.headers["Authorization"] == "Bearer k"


def test_call_groq_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(optimizer.ProviderError) as ei:
        optimizer.call_groq("idea", None)
    assert ei.value.provider == "groq"


def test_call_nvidia_uses_alias_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "k2")
    with patch("urllib.request.urlopen", return_value=_fake_response(OK_PAYLOAD)) as m:
        optimizer.call_nvidia("idea", None)
    req = m.call_args.args[0]
    assert req.full_url == optimizer.NVIDIA_URL
    assert req.headers["Authorization"] == "Bearer k2"


def test_post_chat_http_error_wraps_as_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    err = urllib.error.HTTPError(
        url=optimizer.GROQ_URL,
        code=429,
        msg="Too Many Requests",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(b'{"error":"rate limited"}'),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(optimizer.ProviderError) as ei:
            optimizer.call_groq("idea", None)
    assert "HTTP 429" in str(ei.value)


def test_post_chat_url_error_wraps_as_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
        with pytest.raises(optimizer.ProviderError) as ei:
            optimizer.call_groq("idea", None)
    assert "network error" in str(ei.value)


def test_post_chat_bad_json_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    with patch(
        "urllib.request.urlopen",
        return_value=_fake_response({"unexpected": "shape"}),
    ):
        with pytest.raises(optimizer.ProviderError) as ei:
            optimizer.call_groq("idea", None)
    assert "unexpected response shape" in str(ei.value)


def test_post_chat_empty_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    payload = {"choices": [{"message": {"content": "   "}}]}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        with pytest.raises(optimizer.ProviderError) as ei:
            optimizer.call_groq("idea", None)
    assert "empty completion" in str(ei.value)


def test_optimize_auto_falls_back_to_nvidia(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_groq(idea: str, model: str | None) -> str:
        raise optimizer.ProviderError("groq", "GROQ_API_KEY is not set")

    def ok_nvidia(idea: str, model: str | None) -> str:
        return "OPT"

    monkeypatch.setattr(optimizer, "call_groq", fail_groq)
    monkeypatch.setattr(optimizer, "call_nvidia", ok_nvidia)
    res = optimizer.optimize("idea", "auto", None)
    assert res.prompt == "OPT"
    assert res.provider == "nvidia"


def test_optimize_auto_raises_when_both_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(p: str):  # type: ignore[no-untyped-def]
        def _f(idea: str, model: str | None) -> str:
            raise optimizer.ProviderError(p, "down")
        return _f

    monkeypatch.setattr(optimizer, "call_groq", fail("groq"))
    monkeypatch.setattr(optimizer, "call_nvidia", fail("nvidia"))
    with pytest.raises(optimizer.ProviderError) as ei:
        optimizer.optimize("idea", "auto", None)
    assert "groq" in str(ei.value) and "nvidia" in str(ei.value)


def test_optimize_groq_only_does_not_call_nvidia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"nvidia": 0}

    def ok_groq(idea: str, model: str | None) -> str:
        return "GROQ_OUT"

    def track_nvidia(idea: str, model: str | None) -> str:
        called["nvidia"] += 1
        return "NV_OUT"

    monkeypatch.setattr(optimizer, "call_groq", ok_groq)
    monkeypatch.setattr(optimizer, "call_nvidia", track_nvidia)
    res = optimizer.optimize("idea", "groq", None)
    assert res.provider == "groq"
    assert called["nvidia"] == 0


def test_optimize_empty_idea_raises() -> None:
    with pytest.raises(ValueError):
        optimizer.optimize("   ", "auto", None)


def test_optimize_unknown_provider_raises() -> None:
    with pytest.raises(ValueError):
        optimizer.optimize("idea", "openai", None)


def test_load_dotenv_sets_missing_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FOO_TEST", raising=False)
    monkeypatch.delenv("BAR_TEST", raising=False)
    (tmp_path / ".env").write_text(
        '# comment\nFOO_TEST=hello\nBAR_TEST="quoted value"\n\nINVALID LINE\n'
    )
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    loaded = optimizer.load_dotenv(start=nested)
    assert loaded == tmp_path / ".env"
    assert os.environ["FOO_TEST"] == "hello"
    assert os.environ["BAR_TEST"] == "quoted value"


def test_load_dotenv_does_not_override_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FOO_TEST", "from-shell")
    (tmp_path / ".env").write_text("FOO_TEST=from-file\n")
    optimizer.load_dotenv(start=tmp_path)
    assert os.environ["FOO_TEST"] == "from-shell"


def test_load_dotenv_missing_returns_none(tmp_path: Path) -> None:
    sub = tmp_path / "no-env-anywhere-here"
    sub.mkdir()
    assert optimizer.load_dotenv(start=sub) is None
