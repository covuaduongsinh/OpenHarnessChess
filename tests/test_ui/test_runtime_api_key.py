"""Tests for build_runtime auth failure handling."""

from __future__ import annotations

import pytest

from openharness.ui.runtime import build_runtime


@pytest.mark.asyncio
async def test_build_runtime_exits_cleanly_when_auth_resolution_fails(monkeypatch):
    """build_runtime should raise SystemExit(1) — not ValueError — when auth resolution fails."""

    def fake_resolve_auth(self):
        raise ValueError("No credentials found")

    monkeypatch.setattr("openharness.config.settings.Settings.resolve_auth", fake_resolve_auth)

    with pytest.raises(SystemExit, match="1"):
        await build_runtime(active_profile="claude-api")


@pytest.mark.asyncio
async def test_build_runtime_exits_cleanly_for_openai_format(monkeypatch):
    """Same check for the openai-compatible path."""

    def fake_resolve_auth(self):
        raise ValueError("No credentials found")

    monkeypatch.setattr("openharness.config.settings.Settings.resolve_auth", fake_resolve_auth)

    with pytest.raises(SystemExit, match="1"):
        await build_runtime(active_profile="openai-compatible", api_format="openai")


@pytest.mark.asyncio
async def test_build_runtime_subscription_uses_claude_code_engine(monkeypatch, tmp_path):
    """Claude subscription builds a ClaudeCodeEngine without scraping OAuth tokens."""
    from openharness.api.claude_cli_detect import ClaudeCliStatus
    from openharness.api.claude_code_engine import ClaudeCodeEngine
    from openharness.engine.stream_events import ErrorEvent

    monkeypatch.setenv("OPENHARNESS_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    def fake_status(cli_path=None):
        return ClaudeCliStatus(
            cli_path=None,
            logged_in=False,
            detail="Claude Code CLI not found. Install Claude Code and ensure `claude` is on PATH.",
        )

    monkeypatch.setattr("openharness.api.claude_cli_detect.claude_auth_status", fake_status)
    monkeypatch.setattr("openharness.api.claude_code_engine.claude_auth_status", fake_status)
    monkeypatch.setattr("openharness.api.claude_code_engine.find_claude_cli", lambda: None)

    bundle = await build_runtime(active_profile="claude-subscription", cwd=str(tmp_path))
    try:
        assert isinstance(bundle.engine, ClaudeCodeEngine)
        events = [event async for event in bundle.engine.submit_message("hello")]
        assert any(isinstance(event, ErrorEvent) for event in events)
        assert any("Claude Code" in getattr(event, "message", "") for event in events)
        assert not any("No API key configured" in getattr(event, "message", "") for event in events)
    finally:
        from openharness.ui.runtime import close_runtime

        await close_runtime(bundle)
