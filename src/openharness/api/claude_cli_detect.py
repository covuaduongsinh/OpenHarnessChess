"""Detect the official Claude Code CLI binary and login status.

Used by the Claude Code engine path (subscription via spawn CLI / Agent SDK).
This module never reads OAuth tokens from credentials files for inference.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_EXTRA_BIN_DIRS = (
    "~/.local/bin",
    "~/AppData/Local/Programs/claude",
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "~/.npm-global/bin",
    "~/.volta/bin",
    "~/.bun/bin",
)


@dataclass(frozen=True)
class ClaudeCliStatus:
    """Snapshot of local Claude Code CLI availability."""

    cli_path: str | None
    logged_in: bool
    auth_method: str = ""
    subscription_type: str = ""
    email: str = ""
    version: str = ""
    detail: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.cli_path) and self.logged_in


def _path_candidates() -> str:
    parts = [os.environ.get("PATH", "")]
    for item in _EXTRA_BIN_DIRS:
        try:
            parts.append(str(Path(item).expanduser()))
        except Exception:
            continue
    return os.pathsep.join(p for p in parts if p)


def find_claude_cli() -> str | None:
    """Return the preferred Claude Code binary path, if present."""
    for env_name in ("OPENHARNESS_CLAUDE_CLI", "CLAUDE_CLI", "JAVIS_CLAUDE_CLI"):
        configured = (os.environ.get(env_name) or "").strip()
        if configured:
            path = Path(configured).expanduser()
            if path.exists():
                return str(path.resolve())

    which = shutil.which("claude") or shutil.which("claude", path=_path_candidates())
    if which:
        resolved = str(Path(which).resolve())
        # Prefer host install over SDK-bundled Bun binary when both appear on PATH.
        if "_bundled" not in resolved.replace("\\", "/"):
            return resolved

    home = Path.home()
    for candidate in (
        home / ".local" / "bin" / "claude.exe",
        home / ".local" / "bin" / "claude",
        home / "AppData" / "Roaming" / "npm" / "claude.cmd",
        home / "AppData" / "Roaming" / "npm" / "claude",
    ):
        if candidate.exists():
            return str(candidate.resolve())
    return None


def _run_claude(cli: str, *args: str, timeout: float = 25.0) -> subprocess.CompletedProcess[str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        [cli, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=creationflags,
    )


def claude_cli_version(cli_path: str | None = None) -> str:
    """Return `claude --version` output (short)."""
    cli = cli_path or find_claude_cli()
    if not cli:
        return ""
    try:
        result = _run_claude(cli, "--version", timeout=15.0)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    text = (result.stdout or result.stderr or "").strip()
    return text.splitlines()[0].strip() if text else ""


def claude_auth_status(cli_path: str | None = None) -> ClaudeCliStatus:
    """Probe CLI presence and login via `claude auth status` (no token scrape)."""
    cli = cli_path or find_claude_cli()
    if not cli:
        return ClaudeCliStatus(
            cli_path=None,
            logged_in=False,
            detail="Claude Code CLI not found. Install Claude Code and ensure `claude` is on PATH.",
        )

    version = claude_cli_version(cli)
    try:
        result = _run_claude(cli, "auth", "status", "--json", timeout=30.0)
    except subprocess.TimeoutExpired:
        return ClaudeCliStatus(
            cli_path=cli,
            logged_in=False,
            version=version,
            detail="Timed out while checking Claude Code auth status.",
        )
    except OSError as exc:
        return ClaudeCliStatus(
            cli_path=cli,
            logged_in=False,
            version=version,
            detail=f"Failed to run Claude Code CLI: {exc}",
        )

    payload = _parse_auth_json(result.stdout) or _parse_auth_json(result.stderr)
    if payload is None:
        # Older CLIs may only support text status.
        combined = f"{result.stdout}\n{result.stderr}".lower()
        logged_in = "logged in" in combined or "authenticated" in combined
        if result.returncode == 0 and not combined.strip():
            logged_in = True
        return ClaudeCliStatus(
            cli_path=cli,
            logged_in=logged_in,
            version=version,
            detail="" if logged_in else "Claude Code is not logged in. Run `claude auth login`.",
        )

    logged_in = bool(payload.get("loggedIn") or payload.get("logged_in") or payload.get("authenticated"))
    return ClaudeCliStatus(
        cli_path=cli,
        logged_in=logged_in,
        auth_method=str(payload.get("authMethod") or payload.get("auth_method") or ""),
        subscription_type=str(payload.get("subscriptionType") or payload.get("subscription_type") or ""),
        email=str(payload.get("email") or ""),
        version=version,
        detail="" if logged_in else "Claude Code is not logged in. Run `claude auth login`.",
    )


def _parse_auth_json(raw: str | None) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    # Prefer the last JSON object in output (hooks may print noise first).
    for chunk in reversed(text.splitlines()):
        chunk = chunk.strip()
        if not chunk.startswith("{"):
            continue
        try:
            data = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def uses_claude_code_engine(settings: Any) -> bool:
    """Return True when the active profile should spawn Claude Code (not OAuth API)."""
    provider = str(getattr(settings, "provider", "") or "").strip()
    if provider in {"anthropic_claude", "anthropic_claude_code"}:
        return True
    try:
        _, profile = settings.resolve_profile()
    except Exception:
        return False
    auth_source = str(getattr(profile, "auth_source", "") or "").strip()
    api_format = str(getattr(profile, "api_format", "") or getattr(settings, "api_format", "") or "").strip()
    return auth_source in {"claude_subscription", "claude_code_cli"} or api_format == "claude_code"
