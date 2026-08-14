"""Claude Code engine: spawn official `claude` via Agent SDK (subscription path).

Unlike AnthropicApiClient + OAuth token scrape, this engine never reads
~/.claude/.credentials.json for inference. Anthropic bills the request as
Claude Code (included Pro/Max usage when the CLI is logged in).

Architecture note: Agent SDK runs Claude Code's own agentic loop and tools.
OpenHarness tools are not executed on this path.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, AsyncIterator

from openharness.api.claude_cli_detect import claude_auth_status, find_claude_cli
from openharness.api.client import SupportsStreamingMessages
from openharness.api.usage import UsageSnapshot
from openharness.engine.cost_tracker import CostTracker
from openharness.engine.messages import ConversationMessage, TextBlock
from openharness.engine.stream_events import (
    AssistantTextDelta,
    AssistantTurnComplete,
    ErrorEvent,
    StatusEvent,
    StreamEvent,
    ToolExecutionCompleted,
    ToolExecutionStarted,
)
from openharness.permissions.checker import PermissionChecker

log = logging.getLogger(__name__)

_ACTIVE_CLIENTS: dict[Any, asyncio.AbstractEventLoop] = {}
_ACTIVE_LOCK = threading.Lock()


class _UnusedStreamingClient:
    """Placeholder client so hooks/runtime keep a SupportsStreamingMessages object."""

    async def stream_message(self, request):  # type: ignore[no-untyped-def]
        raise RuntimeError(
            "Claude Code engine path does not use OpenHarness model API clients. "
            "Model calls go through the official `claude` binary via Agent SDK."
        )

    async def close(self) -> None:
        return None


def map_sdk_message_to_events(msg: Any) -> tuple[list[StreamEvent], str | None, UsageSnapshot | None, bool]:
    """Map one SDK message into OpenHarness stream events.

    Returns (events, session_id, usage, is_result).
    Pure helper — unit-tested without a live CLI.
    """
    events: list[StreamEvent] = []
    session_id: str | None = None
    usage: UsageSnapshot | None = None
    is_result = False

    name = type(msg).__name__
    module = type(msg).__module__

    # Prefer duck-typing over hard import so tests can pass simple stand-ins.
    if name == "SystemMessage":
        data = getattr(msg, "data", None) or {}
        if isinstance(data, dict):
            sid = data.get("session_id")
            if sid:
                session_id = str(sid)
        return events, session_id, usage, is_result

    if name == "AssistantMessage":
        for block in getattr(msg, "content", None) or []:
            bname = type(block).__name__
            if bname == "TextBlock":
                text = getattr(block, "text", "") or ""
                if text:
                    events.append(AssistantTextDelta(text=text))
            elif bname == "ToolUseBlock":
                events.append(
                    ToolExecutionStarted(
                        tool_name=str(getattr(block, "name", "") or ""),
                        tool_input=dict(getattr(block, "input", None) or {}),
                    )
                )
        return events, session_id, usage, is_result

    if name == "UserMessage":
        content = getattr(msg, "content", None)
        if isinstance(content, list):
            for block in content:
                if type(block).__name__ != "ToolResultBlock":
                    continue
                raw = getattr(block, "content", "")
                if isinstance(raw, list):
                    parts = []
                    for item in raw:
                        if isinstance(item, dict):
                            parts.append(str(item.get("text", "")))
                        else:
                            parts.append(str(item))
                    text = " ".join(parts)
                else:
                    text = str(raw or "")
                events.append(
                    ToolExecutionCompleted(
                        tool_name="claude_code_tool",
                        output=text[:4000],
                        is_error=bool(getattr(block, "is_error", False)),
                    )
                )
        return events, session_id, usage, is_result

    if name == "ResultMessage":
        is_result = True
        session_id = str(getattr(msg, "session_id", "") or "") or None
        raw_usage = getattr(msg, "usage", None) or {}
        if isinstance(raw_usage, dict):
            cache_read = int(raw_usage.get("cache_read_input_tokens") or 0)
            cache_create = int(raw_usage.get("cache_creation_input_tokens") or 0)
            input_tokens = int(raw_usage.get("input_tokens") or 0) + cache_read + cache_create
            output_tokens = int(raw_usage.get("output_tokens") or 0)
            usage = UsageSnapshot(input_tokens=input_tokens, output_tokens=output_tokens)
        result_text = str(getattr(msg, "result", "") or "")
        is_error = bool(getattr(msg, "is_error", False))
        if is_error and not result_text.strip():
            subtype = getattr(msg, "subtype", "") or "error"
            events.append(
                ErrorEvent(
                    message=(
                        f"Claude Code finished with an error ({subtype}) and no text. "
                        "Retry the prompt, or run `claude auth login` if auth expired."
                    ),
                    recoverable=True,
                )
            )
        # Final assistant message for history (even if empty).
        events.append(
            AssistantTurnComplete(
                message=ConversationMessage(
                    role="assistant",
                    content=[TextBlock(text=result_text)] if result_text else [],
                ),
                usage=usage or UsageSnapshot(),
            )
        )
        return events, session_id, usage, is_result

    # Ignore hook/rate-limit noise in the stream.
    if name in {
        "HookEventMessage",
        "RateLimitEvent",
        "TaskStartedMessage",
        "TaskProgressMessage",
        "TaskUpdatedMessage",
        "TaskNotificationMessage",
    }:
        return events, session_id, usage, is_result

    log.debug("Ignoring SDK message type %s (%s)", name, module)
    return events, session_id, usage, is_result


class ClaudeCodeEngine:
    """Query-engine stand-in that delegates turns to Claude Code Agent SDK."""

    def __init__(
        self,
        *,
        cwd: str | Path,
        model: str,
        system_prompt: str = "",
        permission_mode: str = "default",
        tool_metadata: dict[str, object] | None = None,
        cli_path: str | None = None,
    ) -> None:
        self._cwd = Path(cwd).resolve()
        self._model = model
        self._system_prompt = system_prompt
        self._permission_mode = permission_mode
        self._tool_metadata = tool_metadata or {}
        self._cli_path = cli_path or find_claude_cli()
        self._messages: list[ConversationMessage] = []
        self._cost_tracker = CostTracker()
        self._max_turns: int | None = None
        self._effort: str | None = None
        self._api_client: SupportsStreamingMessages = _UnusedStreamingClient()
        self._session_id: str | None = None
        self._tmp_files: list[Path] = []
        self._permission_checker: PermissionChecker | None = None

    # --- QueryEngine-compatible surface ---------------------------------

    @property
    def messages(self) -> list[ConversationMessage]:
        return list(self._messages)

    @property
    def max_turns(self) -> int | None:
        return self._max_turns

    @property
    def api_client(self) -> SupportsStreamingMessages:
        return self._api_client

    @property
    def model(self) -> str:
        return self._model

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def tool_metadata(self) -> dict[str, object]:
        return self._tool_metadata

    @property
    def total_usage(self):
        return self._cost_tracker.total

    def set_system_prompt(self, prompt: str) -> None:
        self._system_prompt = prompt

    def set_model(self, model: str) -> None:
        self._model = model

    def set_effort(self, effort: str | None) -> None:
        self._effort = effort

    def set_api_client(self, api_client: SupportsStreamingMessages) -> None:
        self._api_client = api_client

    def set_max_turns(self, max_turns: int | None) -> None:
        self._max_turns = None if max_turns is None else max(1, int(max_turns))

    def set_permission_checker(self, checker: PermissionChecker) -> None:
        self._permission_checker = checker

    def load_messages(self, messages: list[ConversationMessage]) -> None:
        self._messages = list(messages)

    def clear(self) -> None:
        self._messages.clear()
        self._cost_tracker = CostTracker()
        self._session_id = None

    def has_pending_continuation(self) -> bool:
        return False

    async def continue_pending(self, *, max_turns: int | None = None) -> AsyncIterator[StreamEvent]:
        yield ErrorEvent(
            message="Continue-pending is not used on the Claude Code engine path "
            "(Claude Code completes the agentic loop in one turn).",
            recoverable=True,
        )
        return
        yield  # pragma: no cover

    async def submit_message(self, prompt: str | ConversationMessage) -> AsyncIterator[StreamEvent]:
        user_message = (
            prompt
            if isinstance(prompt, ConversationMessage)
            else ConversationMessage.from_user_text(prompt)
        )
        self._messages.append(user_message)
        text = user_message.text.strip()
        if not text:
            yield ErrorEvent(message="Empty prompt.", recoverable=True)
            return

        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        except ImportError:
            yield ErrorEvent(
                message=(
                    "claude-agent-sdk is not installed. "
                    "Install with: pip install 'openharness-ai[claude-code]' "
                    "or: uv pip install claude-agent-sdk"
                ),
                recoverable=False,
            )
            return

        status = claude_auth_status(self._cli_path)
        if not status.cli_path:
            yield ErrorEvent(
                message=status.detail or "Claude Code CLI not found on PATH.",
                recoverable=False,
            )
            return
        if not status.logged_in:
            yield ErrorEvent(
                message=status.detail or "Claude Code is not logged in. Run `claude auth login`.",
                recoverable=False,
            )
            return

        self._cli_path = status.cli_path
        yield StatusEvent(message=f"Claude Code engine ({status.subscription_type or 'subscription'})")

        options = self._build_options(ClaudeAgentOptions)
        client = ClaudeSDKClient(options=options)
        loop = asyncio.get_running_loop()
        assistant_chunks: list[str] = []
        final_message: ConversationMessage | None = None
        try:
            await client.connect()
            with _ACTIVE_LOCK:
                _ACTIVE_CLIENTS[client] = loop
            await client.query(text)
            async for msg in client.receive_response():
                events, session_id, usage, is_result = map_sdk_message_to_events(msg)
                if session_id:
                    self._session_id = session_id
                    self._tool_metadata["claude_code_session_id"] = session_id
                for event in events:
                    if isinstance(event, AssistantTextDelta):
                        assistant_chunks.append(event.text)
                    if isinstance(event, AssistantTurnComplete):
                        final_message = event.message
                        if usage is not None:
                            self._cost_tracker.add(usage)
                    yield event
                if is_result:
                    break
        except Exception as exc:
            message = str(exc)
            if "extra usage" in message.lower():
                message = (
                    f"{message}\n"
                    "Claude Code engine still hit extra-usage billing. "
                    "Confirm `claude -p` works with the same account, then retry."
                )
            yield ErrorEvent(message=f"Claude Code engine error: {message}", recoverable=True)
        finally:
            with _ACTIVE_LOCK:
                _ACTIVE_CLIENTS.pop(client, None)
            try:
                await client.disconnect()
            except Exception:
                pass
            self._cleanup_tmp()

        if final_message is None:
            # Some streams only emit text deltas; synthesize the turn complete.
            joined = "".join(assistant_chunks)
            if joined:
                final_message = ConversationMessage(
                    role="assistant",
                    content=[TextBlock(text=joined)],
                )
                yield AssistantTurnComplete(message=final_message, usage=UsageSnapshot())
        if final_message is not None:
            self._messages.append(final_message)

    # --- SDK options ----------------------------------------------------

    def _build_options(self, options_cls: Any) -> Any:
        fields = getattr(options_cls, "__dataclass_fields__", {})
        kw: dict[str, Any] = {"cwd": str(self._cwd)}
        if "cli_path" in fields and self._cli_path:
            kw["cli_path"] = self._cli_path
        if "model" in fields and self._model and self._model not in {"default", "sonnet", "opus", "haiku"}:
            # Pass explicit model ids; aliases are left to Claude Code defaults.
            if self._model.startswith("claude-"):
                kw["model"] = self._model
        if "resume" in fields and self._session_id:
            kw["resume"] = self._session_id

        # Permission: map OH modes loosely onto Claude Code.
        mode = (self._permission_mode or "default").lower()
        if "permission_mode" in fields:
            if mode in {"bypasspermissions", "full", "auto"}:
                kw["permission_mode"] = "bypassPermissions"
            else:
                kw["permission_mode"] = "default"
        # Always load user/project settings so CLAUDE.md / ambient MCP work.
        if "setting_sources" in fields:
            kw["setting_sources"] = ["user", "project", "local"]

        if "system_prompt" in fields:
            prompt = (self._system_prompt or "").strip()
            if prompt and "extra_args" in fields:
                path = self._write_sysprompt_file(prompt)
                kw["system_prompt"] = {"type": "preset", "preset": "claude_code"}
                kw["extra_args"] = {"append-system-prompt-file": str(path)}
            elif prompt:
                # Fallback: append inline (may fail on huge prompts on Windows).
                kw["system_prompt"] = {
                    "type": "preset",
                    "preset": "claude_code",
                    "append": prompt[:12000],
                }
            else:
                kw["system_prompt"] = {"type": "preset", "preset": "claude_code"}

        if "max_buffer_size" in fields:
            kw["max_buffer_size"] = 32 * 1024 * 1024

        # Never inject empty ANTHROPIC_API_KEY; leave env to CLI login session.
        if "env" in fields:
            env = {k: v for k, v in os.environ.items() if k not in {"ANTHROPIC_AUTH_TOKEN"}}
            # Strip API key only when we want pure subscription; if user set key intentionally, keep it.
            # Subscription path: do not force key. Leave as-is so CLI can prefer login when key absent.
            kw["env"] = env

        # Nudge init timeout for heavy MCP setups (milliseconds).
        if not os.environ.get("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT"):
            os.environ["CLAUDE_CODE_STREAM_CLOSE_TIMEOUT"] = "300000"

        return options_cls(**kw)

    def _write_sysprompt_file(self, prompt: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".txt",
            prefix="openh-sysprompt-",
            delete=False,
        )
        with tmp:
            tmp.write(prompt)
            path = Path(tmp.name)
        self._tmp_files.append(path)
        return path

    def _cleanup_tmp(self) -> None:
        for path in self._tmp_files:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        self._tmp_files.clear()


def interrupt_all_claude_code_sessions() -> int:
    """Best-effort interrupt of active Claude SDK clients."""
    with _ACTIVE_LOCK:
        items = list(_ACTIVE_CLIENTS.items())
    count = 0
    for client, loop in items:
        try:
            asyncio.run_coroutine_threadsafe(client.interrupt(), loop)
            count += 1
        except Exception:
            continue
    return count
