"""Antigravity CLI engine: spawn official `agy` (Google personal subscription path).

Gemini CLI personal tiers were cut by Google (2026-06); Antigravity CLI is the
current subscription-oriented Google agent CLI.
"""

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


def find_antigravity_cli() -> str | None:
    for env_name in ("OPENHARNESS_AGY_CLI", "AGY_CLI", "JAVIS_AGY_BIN"):
        raw = (os.environ.get(env_name) or "").strip()
        if raw and Path(raw).expanduser().exists():
            return str(Path(raw).expanduser().resolve())

    home = home_dir()
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        local / "agy" / "bin" / "agy.EXE",
        local / "agy" / "bin" / "agy.exe",
        local / "agy" / "bin" / "agy",
        home / ".local" / "bin" / "agy",
        home / ".antigravity" / "bin" / "agy",
        Path("/usr/local/bin/agy"),
        Path("/opt/homebrew/bin/agy"),
    ]
    path = which_binary(
        "agy",
        [
            local / "agy" / "bin",
            home / ".local" / "bin",
            home / ".antigravity" / "bin",
        ],
    )
    if path:
        return path
    for candidate in candidates:
        try:
            if candidate.exists():
                return str(candidate.resolve())
        except OSError:
            continue
    return None


def antigravity_cli_status() -> tuple[bool, str, str | None]:
    cli = find_antigravity_cli()
    if not cli:
        return (
            False,
            "Antigravity CLI (`agy`) not found. Install: "
            "irm https://antigravity.google/cli/install.ps1 | iex  then run `agy` once to login.",
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
        return False, f"Failed to run Antigravity CLI: {exc}", cli
    version = (result.stdout or result.stderr or "").strip().splitlines()
    ver = version[0] if version else "ready"
    if result.returncode != 0:
        return False, f"Antigravity CLI not usable: {ver}", cli
    return True, ver, cli


def uses_antigravity_cli_engine(settings: Any) -> bool:
    provider = str(getattr(settings, "provider", "") or "").strip()
    if provider in {"antigravity", "google_antigravity", "agy"}:
        return True
    try:
        _, profile = settings.resolve_profile()
    except Exception:
        return False
    auth = str(getattr(profile, "auth_source", "") or "").strip()
    return auth in {"antigravity_cli", "agy_cli"}


def map_agy_json_line(line: str) -> list[StreamEvent]:
    """Map Antigravity `--output-format stream-json` lines (pure)."""
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
    event = str(data.get("event") or "")
    if event == "step_update":
        step = data.get("step_update") if isinstance(data.get("step_update"), dict) else {}
        delta = step.get("text_delta") or ""
        if delta:
            events.append(AssistantTextDelta(text=str(delta)))
        step_type = str(step.get("step_type") or "")
        if "tool" in step_type or step_type in {"run_command", "write_to_file", "replace_file_content"}:
            events.append(ToolExecutionStarted(tool_name=step_type, tool_input=dict(step)))
        return events
    if event == "result":
        # finalize handles full result; still surface response text if no deltas streamed
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
        response = result.get("response") or ""
        status = str(result.get("status") or "")
        if status and status.upper() not in {"SUCCESS", "OK", ""}:
            events.append(ErrorEvent(message=f"Antigravity status={status}: {response}"[:2000]))
        elif response and not events:
            # Only if we need fallback; caller finalize will also use collected text
            pass
        return events
    if event == "error":
        events.append(ErrorEvent(message=str(data.get("error") or data.get("message") or text)[:2000]))
    return events


class AntigravityCliEngine(SubprocessCliEngine):
    engine_label = "Antigravity CLI"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._usage = UsageSnapshot()
        self._final_response = ""

    def resolve_cli_path(self) -> str | None:
        return self._cli_path or find_antigravity_cli()

    def readiness_error(self) -> str | None:
        ready, detail, path = antigravity_cli_status()
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
        args = [
            cli,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--dangerously-skip-permissions",
        ]
        model = (self._model or "").strip()
        # Ignore leftover models from other OpenHarness profiles (e.g. gpt-5.4, claude-*).
        if model and model not in {"default", "best"} and not model.startswith(
            ("gpt-", "o1", "o3", "o4", "claude-", "kimi", "gemini-")
        ):
            args += ["--model", model]
        if self._effort:
            args += ["--effort", self._effort]
        return args

    def parse_stdout_line(self, line: str) -> list[StreamEvent]:
        # Capture usage/result metadata
        try:
            data = json.loads(line.strip())
            if isinstance(data, dict) and data.get("event") == "result":
                result = data.get("result") if isinstance(data.get("result"), dict) else {}
                self._final_response = str(result.get("response") or "")
                usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
                self._usage = UsageSnapshot(
                    input_tokens=int(usage.get("input_tokens") or 0),
                    output_tokens=int(usage.get("output_tokens") or 0),
                )
        except Exception:
            pass
        return map_agy_json_line(line)

    def finalize_from_stdout(self, collected_text: str, returncode: int) -> list[StreamEvent]:
        text = collected_text or self._final_response
        message = ConversationMessage(
            role="assistant",
            content=[TextBlock(text=text)] if text else [],
        )
        return [AssistantTurnComplete(message=message, usage=self._usage)]
