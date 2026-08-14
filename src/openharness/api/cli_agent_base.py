"""Shared base for OpenHarness engines that spawn official agent CLIs.

Used for Codex / Grok / Antigravity (and similar) subscription paths:
spawn the vendor binary, do not scrape OAuth tokens for HTTP API calls.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, AsyncIterator

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
)
from openharness.permissions.checker import PermissionChecker

log = logging.getLogger(__name__)

_ACTIVE_PROCS: dict[subprocess.Popen[str], str] = {}
_PROC_LOCK = threading.Lock()


class _UnusedStreamingClient:
    async def stream_message(self, request):  # type: ignore[no-untyped-def]
        raise RuntimeError("CLI agent engine does not use OpenHarness model API clients.")

    async def close(self) -> None:
        return None


class SubprocessCliEngine(ABC):
    """QueryEngine-compatible surface that runs one vendor CLI agent turn."""

    engine_label: str = "cli-agent"

    def __init__(
        self,
        *,
        cwd: str | Path,
        model: str = "default",
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
        self._cli_path = cli_path
        self._messages: list[ConversationMessage] = []
        self._cost_tracker = CostTracker()
        self._max_turns: int | None = None
        self._effort: str | None = None
        self._api_client: SupportsStreamingMessages = _UnusedStreamingClient()
        self._permission_checker: PermissionChecker | None = None
        self._session_id: str | None = None

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
            message=f"Continue-pending is not used on the {self.engine_label} path.",
            recoverable=True,
        )
        return
        yield  # pragma: no cover

    @abstractmethod
    def resolve_cli_path(self) -> str | None:
        """Return path to the vendor CLI binary."""

    @abstractmethod
    def readiness_error(self) -> str | None:
        """Return a user-facing error if the CLI is not ready, else None."""

    @abstractmethod
    def build_command(self, prompt: str) -> list[str]:
        """Build argv for a non-interactive agent turn."""

    @abstractmethod
    def feed_prompt_via_stdin(self) -> bool:
        """True if the prompt is written to stdin instead of argv."""

    def prompt_prefix(self) -> str:
        """Optional short instructions prepended to the user prompt (keep tiny on Windows)."""
        return ""

    def parse_stdout_line(self, line: str) -> list[StreamEvent]:
        """Parse one stdout line into stream events (default: plain text passthrough)."""
        text = line.rstrip("\n")
        if not text:
            return []
        return [AssistantTextDelta(text=text + "\n")]

    def finalize_from_stdout(self, collected_text: str, returncode: int) -> list[StreamEvent]:
        """Emit terminal events after process exit."""
        events: list[StreamEvent] = []
        if returncode not in (0, None) and not collected_text.strip():
            events.append(
                ErrorEvent(
                    message=f"{self.engine_label} exited with code {returncode}.",
                    recoverable=True,
                )
            )
        message = ConversationMessage(
            role="assistant",
            content=[TextBlock(text=collected_text)] if collected_text else [],
        )
        events.append(AssistantTurnComplete(message=message, usage=UsageSnapshot()))
        return events

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

        # Do NOT dump the full OpenHarness system prompt into argv/stdin by default.
        # Vendor CLIs already load their own project instructions (AGENTS.md / CLAUDE.md /
        # settings). Prefixing OH's multi-10k prompt triggers Windows CreateProcess
        # WinError 206 (command line too long) for -p engines.
        extra = self.prompt_prefix()
        if extra:
            text = f"{extra}\n\n{text}"

        cli = self.resolve_cli_path()
        self._cli_path = cli
        err = self.readiness_error()
        if err:
            yield ErrorEvent(message=err, recoverable=False)
            return
        if not cli:
            yield ErrorEvent(
                message=f"{self.engine_label}: CLI binary not found.",
                recoverable=False,
            )
            return

        yield StatusEvent(message=f"{self.engine_label} ({cli})")
        try:
            cmd = self.build_command(text if not self.feed_prompt_via_stdin() else "")
        except Exception as exc:
            yield ErrorEvent(message=f"{self.engine_label}: failed to build command: {exc}", recoverable=True)
            return

        stdin_payload = text if self.feed_prompt_via_stdin() else None
        collected_parts: list[str] = []
        returncode = 0
        try:
            async for event in self._run_process(cmd, stdin_payload):
                if isinstance(event, AssistantTextDelta):
                    collected_parts.append(event.text)
                yield event
        except Exception as exc:
            yield ErrorEvent(message=f"{self.engine_label} error: {exc}", recoverable=True)
            return

        collected = "".join(collected_parts)
        # Prefer non-duplicated final text: if finalize rebuilds from collected, strip trailing
        # complete only when we already streamed text.
        for event in self.finalize_from_stdout(collected, returncode):
            if isinstance(event, AssistantTurnComplete):
                self._messages.append(event.message)
                if event.usage.input_tokens or event.usage.output_tokens:
                    self._cost_tracker.add(event.usage)
            yield event

    async def _run_process(
        self,
        cmd: list[str],
        stdin_payload: str | None,
    ) -> AsyncIterator[StreamEvent]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Any] = asyncio.Queue()
        sentinel = object()
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        def worker() -> None:
            proc: subprocess.Popen[str] | None = None
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE if stdin_payload is not None else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(self._cwd),
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=creationflags,
                )
                with _PROC_LOCK:
                    _ACTIVE_PROCS[proc] = self.engine_label

                if stdin_payload is not None and proc.stdin is not None:
                    try:
                        proc.stdin.write(stdin_payload)
                        proc.stdin.close()
                    except Exception:
                        pass

                assert proc.stdout is not None
                for line in proc.stdout:
                    for event in self.parse_stdout_line(line):
                        loop.call_soon_threadsafe(queue.put_nowait, event)

                stderr = ""
                if proc.stderr is not None:
                    stderr = proc.stderr.read() or ""
                code = proc.wait()
                if code not in (0, None) and stderr.strip():
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        ErrorEvent(
                            message=f"{self.engine_label} stderr: {stderr.strip()[:2000]}",
                            recoverable=True,
                        ),
                    )
                loop.call_soon_threadsafe(queue.put_nowait, ("__exit__", code))
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, ErrorEvent(message=str(exc), recoverable=True))
                loop.call_soon_threadsafe(queue.put_nowait, ("__exit__", 1))
            finally:
                if proc is not None:
                    with _PROC_LOCK:
                        _ACTIVE_PROCS.pop(proc, None)
                loop.call_soon_threadsafe(queue.put_nowait, sentinel)

        threading.Thread(target=worker, daemon=True).start()
        while True:
            item = await queue.get()
            if item is sentinel:
                break
            if isinstance(item, tuple) and item and item[0] == "__exit__":
                # return code consumed by finalize via collected text only
                continue
            yield item


def kill_all_cli_agent_processes() -> int:
    """Best-effort kill of active CLI agent subprocesses."""
    with _PROC_LOCK:
        procs = list(_ACTIVE_PROCS.keys())
    n = 0
    for proc in procs:
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            else:
                proc.terminate()
            n += 1
        except Exception:
            continue
    return n


def home_dir() -> Path:
    for key in ("USERPROFILE", "HOME"):
        raw = os.environ.get(key)
        if raw:
            path = Path(raw)
            if path.exists():
                return path
    try:
        return Path.home()
    except Exception:
        return Path(".")


def which_binary(name: str, extra_dirs: list[Path] | None = None) -> str | None:
    import shutil

    path_parts = [os.environ.get("PATH", "")]
    for d in extra_dirs or []:
        path_parts.append(str(d))
    search_path = os.pathsep.join(p for p in path_parts if p)
    found = shutil.which(name) or shutil.which(name, path=search_path)
    if found and "windowsapps" not in found.lower():
        return found
    return found
