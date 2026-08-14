"""Spike: Claude Agent SDK with local `claude` CLI (subscription auth)."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path


def find_claude_cli() -> str | None:
    env = (os.environ.get("OPENHARNESS_CLAUDE_CLI") or os.environ.get("CLAUDE_CLI") or "").strip()
    if env and Path(env).exists():
        return env
    which = shutil.which("claude")
    if which:
        return which
    candidates = [
        Path.home() / ".local" / "bin" / "claude.exe",
        Path.home() / ".local" / "bin" / "claude",
        Path(r"C:\Program Files\nodejs\claude.cmd"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


async def main() -> int:
    # Do not inject API keys — use Claude Code login session.
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        os.environ.pop(key, None)

    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ClaudeSDKClient,
            ResultMessage,
            TextBlock,
        )
    except ImportError as exc:
        print(f"FAIL import claude_agent_sdk: {exc}", file=sys.stderr)
        return 2

    cli = find_claude_cli()
    print(f"cli_path={cli}")
    if not cli:
        print("FAIL: claude binary not found", file=sys.stderr)
        return 2

    fields = getattr(ClaudeAgentOptions, "__dataclass_fields__", {})
    kw: dict = {"cwd": str(Path.cwd())}
    if "cli_path" in fields:
        kw["cli_path"] = cli
    if "permission_mode" in fields:
        kw["permission_mode"] = "bypassPermissions"
    if "setting_sources" in fields:
        kw["setting_sources"] = ["user", "project", "local"]
    if "system_prompt" in fields:
        kw["system_prompt"] = {"type": "preset", "preset": "claude_code"}

    opts = ClaudeAgentOptions(**kw)
    client = ClaudeSDKClient(options=opts)
    texts: list[str] = []
    try:
        await client.connect()
        await client.query("Reply with exactly: OK")
        async for msg in client.receive_response():
            name = type(msg).__name__
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock) and (block.text or "").strip():
                        texts.append(block.text)
                        print(f"TEXT {block.text!r}")
            elif isinstance(msg, ResultMessage):
                print(
                    f"RESULT is_error={msg.is_error} "
                    f"result={(msg.result or '')[:200]!r} usage={msg.usage}"
                )
            else:
                print(f"MSG {name}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    joined = "".join(texts).strip()
    print(f"JOINED={joined!r}")
    if "OK" in joined and "extra usage" not in joined.lower():
        print("SPIKE_OK")
        return 0
    print("SPIKE_FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
