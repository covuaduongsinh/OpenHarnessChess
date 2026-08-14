"""Grok Build CLI engine: spawn official `grok` (SuperGrok / X Premium+)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openharness.api.cli_agent_base import SubprocessCliEngine, home_dir, which_binary
from openharness.api.usage import UsageSnapshot
from openharness.engine.messages import ConversationMessage, TextBlock
from openharness.engine.stream_events import (
    AssistantTextDelta,
    AssistantTurnComplete,
    ErrorEvent,
    StreamEvent,
    ToolExecutionStarted,
)


def find_grok_cli() -> str | None:
    for env_name in ("OPENHARNESS_GROK_CLI", "GROK_CLI"):
        raw = (os.environ.get(env_name) or "").strip()
        if raw and Path(raw).expanduser().exists():
            return str(Path(raw).expanduser().resolve())

    home = home_dir()
    candidates = [
        home / ".grok" / "bin" / "grok.exe",
        home / ".grok" / "bin" / "grok",
        home / ".local" / "bin" / "grok.exe",
        home / ".local" / "bin" / "grok",
    ]
    path = which_binary("grok", [home / ".grok" / "bin", home / ".local" / "bin"])
    if path:
        return path
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return None


def grok_cli_status() -> tuple[bool, str, str | None]:
    cli = find_grok_cli()
    if not cli:
        return (
            False,
            "Grok Build CLI not found. Install from https://x.ai/cli then run `grok login`.",
            None,
        )
    import subprocess

    try:
        result = subprocess.run(
            [cli, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        return False, f"Failed to run Grok CLI: {exc}", cli
    if result.returncode != 0:
        return False, f"Grok CLI not usable: {(result.stderr or result.stdout)[:300]}", cli
    return True, (result.stdout or result.stderr or "ready").strip().splitlines()[0], cli


def uses_grok_cli_engine(settings: Any) -> bool:
    provider = str(getattr(settings, "provider", "") or "").strip()
    if provider in {"grok", "grok_cli", "xai_grok"}:
        return True
    try:
        _, profile = settings.resolve_profile()
    except Exception:
        return False
    auth = str(getattr(profile, "auth_source", "") or "").strip()
    return auth in {"grok_cli", "grok_subscription"}


def map_grok_json_line(line: str) -> list[StreamEvent]:
    """Map Grok `--output-format streaming-json` lines (pure)."""
    text = line.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [AssistantTextDelta(text=line if line.endswith("\n") else line + "\n")]
    if not isinstance(data, dict):
        return []

    events: list[StreamEvent] = []
    kind = str(data.get("type") or "")
    if kind == "text":
        payload = data.get("data")
        if payload is None:
            payload = data.get("text") or data.get("content") or ""
        if str(payload):
            events.append(AssistantTextDelta(text=str(payload)))
    elif kind in {"tool_call", "tool_use", "tool"}:
        name = str(data.get("name") or data.get("tool") or "tool")
        events.append(ToolExecutionStarted(tool_name=name, tool_input=dict(data.get("input") or {})))
    elif kind == "error":
        events.append(ErrorEvent(message=str(data.get("data") or data.get("message") or text)[:2000]))
    # thought / usage / available_commands / end ignored here; finalize handles end.
    return events


class GrokCliEngine(SubprocessCliEngine):
    engine_label = "Grok CLI"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._usage = UsageSnapshot()
        self._saw_text = False

    def resolve_cli_path(self) -> str | None:
        return self._cli_path or find_grok_cli()

    def readiness_error(self) -> str | None:
        ready, detail, path = grok_cli_status()
        if path:
            self._cli_path = path
        if ready:
            return None
        return detail

    def feed_prompt_via_stdin(self) -> bool:
        return False

    def build_command(self, prompt: str) -> list[str]:
        cli = self.resolve_cli_path()
        assert cli
        args = [cli, "-p", prompt, "--output-format", "streaming-json", "--cwd", str(self._cwd)]
        mode = (self._permission_mode or "default").lower()
        if mode in {"bypasspermissions", "full", "auto"}:
            args.append("--always-approve")
        model = (self._model or "").strip()
        if model and model not in {"default", "best"} and not model.startswith(
            ("gpt-", "o1", "o3", "o4", "claude-", "gemini-")
        ):
            # Only pass explicit Grok model ids if the CLI accepts them later.
            pass
        # Avoid hanging on interactive OAuth when already logged in; do not force --oauth.
        return args

    def parse_stdout_line(self, line: str) -> list[StreamEvent]:
        events = map_grok_json_line(line)
        for event in events:
            if isinstance(event, AssistantTextDelta):
                self._saw_text = True
        # Capture usage if present
        try:
            data = json.loads(line.strip())
            if isinstance(data, dict) and data.get("type") == "usage":
                payload = data.get("data") if isinstance(data.get("data"), dict) else data
                if isinstance(payload, dict):
                    self._usage = UsageSnapshot(
                        input_tokens=int(payload.get("input_tokens") or payload.get("prompt_tokens") or 0),
                        output_tokens=int(payload.get("output_tokens") or payload.get("completion_tokens") or 0),
                    )
        except Exception:
            pass
        return events

    def finalize_from_stdout(self, collected_text: str, returncode: int) -> list[StreamEvent]:
        message = ConversationMessage(
            role="assistant",
            content=[TextBlock(text=collected_text)] if collected_text else [],
        )
        return [AssistantTurnComplete(message=message, usage=self._usage)]
