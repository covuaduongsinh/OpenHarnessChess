"""Codex CLI engine: spawn official `codex exec` (ChatGPT subscription).

Does not scrape ~/.codex/auth.json for HTTP API calls — the CLI owns auth.
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
    ToolExecutionCompleted,
    ToolExecutionStarted,
)


def find_codex_cli() -> str | None:
    for env_name in ("OPENHARNESS_CODEX_CLI", "CODEX_CLI", "JAVIS_CODEX_BIN"):
        raw = (os.environ.get(env_name) or "").strip()
        if raw and Path(raw).expanduser().exists():
            return str(Path(raw).expanduser().resolve())

    home = home_dir()
    candidates = [
        home / ".codex" / "plugins" / ".plugin-appserver" / "codex.exe",
        home / ".codex" / ".sandbox-bin" / "codex.exe",
        home / ".codex" / "plugins" / ".plugin-appserver" / "codex",
        home / ".codex" / ".sandbox-bin" / "codex",
        home / ".local" / "bin" / "codex",
        Path(os.environ.get("APPDATA", "")) / "npm" / "codex.cmd",
        Path(os.environ.get("APPDATA", "")) / "npm" / "codex.exe",
    ]
    # Prefer real install over broken WindowsApps aliases.
    path = which_binary("codex", [home / ".local" / "bin", home / ".codex" / "plugins" / ".plugin-appserver"])
    if path and "windowsapps" not in path.lower():
        return path
    for candidate in candidates:
        try:
            if candidate.exists():
                return str(candidate.resolve())
        except OSError:
            continue
    return path


def codex_cli_status() -> tuple[bool, str, str | None]:
    """Return (ready, detail, cli_path)."""
    cli = find_codex_cli()
    if not cli:
        return False, "Codex CLI not found. Install Codex and ensure `codex` is available.", None
    # Probe login via a lightweight subcommand when possible.
    import subprocess

    try:
        result = subprocess.run(
            [cli, "login", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        return False, f"Failed to run Codex CLI: {exc}", cli

    combined = f"{result.stdout}\n{result.stderr}".strip()
    low = combined.lower()
    if "invalid id token" in low or "not logged" in low or "login required" in low:
        return (
            False,
            f"Codex CLI is not logged in (or auth is corrupted). Run `codex login`. Detail: {combined[:300]}",
            cli,
        )
    if result.returncode != 0 and ("error" in low or "invalid" in low):
        return False, f"Codex CLI auth check failed: {combined[:400]}", cli
    return True, "Codex CLI ready", cli


def uses_codex_cli_engine(settings: Any) -> bool:
    provider = str(getattr(settings, "provider", "") or "").strip()
    if provider in {"openai_codex", "codex_cli"}:
        return True
    try:
        _, profile = settings.resolve_profile()
    except Exception:
        return False
    auth = str(getattr(profile, "auth_source", "") or "").strip()
    return auth in {"codex_subscription", "codex_cli"}


def map_codex_json_line(line: str) -> list[StreamEvent]:
    """Map one Codex `--json` NDJSON line to stream events (pure)."""
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
    # Common shapes across Codex versions.
    msg_type = str(data.get("type") or data.get("item_type") or data.get("event") or "")
    if msg_type in {"agent_message", "message", "assistant_message"}:
        content = data.get("text") or data.get("message") or data.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in content
            )
        if str(content).strip():
            events.append(AssistantTextDelta(text=str(content)))
        return events

    if msg_type in {"item.completed", "item_completed"}:
        item = data.get("item") if isinstance(data.get("item"), dict) else data
        item_type = str(item.get("type") or "")
        if item_type in {"agent_message", "message"}:
            content = item.get("text") or item.get("content") or ""
            if str(content).strip():
                events.append(AssistantTextDelta(text=str(content)))
        elif "command" in item_type or "tool" in item_type or "mcp" in item_type:
            name = str(item.get("name") or item.get("command") or item_type)
            events.append(ToolExecutionStarted(tool_name=name, tool_input=dict(item) if isinstance(item, dict) else {}))
            out = str(item.get("output") or item.get("result") or item.get("aggregated_output") or "")
            if out:
                events.append(ToolExecutionCompleted(tool_name=name, output=out[:4000]))
        return events

    if msg_type in {"error", "turn.failed"}:
        events.append(ErrorEvent(message=str(data.get("message") or data.get("error") or text)[:2000]))
        return events

    # Fallback: some builds stream {text: "..."} deltas
    if "text" in data and isinstance(data["text"], str) and data["text"]:
        events.append(AssistantTextDelta(text=data["text"]))
    return events


class CodexCliEngine(SubprocessCliEngine):
    engine_label = "Codex CLI"

    def resolve_cli_path(self) -> str | None:
        return self._cli_path or find_codex_cli()

    def readiness_error(self) -> str | None:
        ready, detail, path = codex_cli_status()
        if path:
            self._cli_path = path
        if ready:
            return None
        return detail

    def feed_prompt_via_stdin(self) -> bool:
        return True

    def build_command(self, prompt: str) -> list[str]:
        cli = self.resolve_cli_path()
        assert cli
        args = [cli]
        mode = (self._permission_mode or "default").lower()
        if mode in {"bypasspermissions", "full", "auto"}:
            args += ["--dangerously-bypass-approvals-and-sandbox"]
        else:
            # Non-interactive: never hang on approval prompts.
            args += ["--dangerously-bypass-approvals-and-sandbox"]
        if self._model and self._model not in {"default", "best"} and self._model.startswith(("gpt-", "o1", "o3", "o4")):
            args += ["-m", self._model]
        args += ["exec", "--json", "--skip-git-repo-check"]
        if self._session_id:
            args += ["resume", self._session_id]
        args.append("-")
        return args

    def parse_stdout_line(self, line: str) -> list[StreamEvent]:
        return map_codex_json_line(line)

    def finalize_from_stdout(self, collected_text: str, returncode: int) -> list[StreamEvent]:
        # Deduplicate: if we already streamed text, still emit turn complete.
        if "invalid id token" in collected_text.lower():
            return [
                ErrorEvent(
                    message="Codex auth is invalid. Run `codex login` and retry.",
                    recoverable=False,
                )
            ]
        message = ConversationMessage(
            role="assistant",
            content=[TextBlock(text=collected_text)] if collected_text else [],
        )
        return [AssistantTurnComplete(message=message, usage=UsageSnapshot())]
