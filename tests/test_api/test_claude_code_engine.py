"""Unit tests for Claude Code engine mapping (no live CLI required)."""

from __future__ import annotations

from types import SimpleNamespace

from openharness.api.claude_code_engine import map_sdk_message_to_events
from openharness.api.claude_cli_detect import uses_claude_code_engine
from openharness.engine.stream_events import (
    AssistantTextDelta,
    AssistantTurnComplete,
    ErrorEvent,
    ToolExecutionCompleted,
    ToolExecutionStarted,
)


class AssistantMessage:
    def __init__(self, content):
        self.content = content


class TextBlock:
    def __init__(self, text):
        self.text = text


class ToolUseBlock:
    def __init__(self, name, input):
        self.name = name
        self.input = input


class UserMessage:
    def __init__(self, content):
        self.content = content


class ToolResultBlock:
    def __init__(self, content, is_error=False):
        self.content = content
        self.is_error = is_error


class ResultMessage:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _Settings:
    def __init__(self, provider: str, auth_source: str = "claude_subscription"):
        self.provider = provider
        self._auth_source = auth_source

    def resolve_profile(self):
        profile = SimpleNamespace(auth_source=self._auth_source, api_format="anthropic")
        return "claude-subscription", profile


def test_uses_claude_code_engine_for_subscription_profile():
    assert uses_claude_code_engine(_Settings("anthropic_claude")) is True
    assert uses_claude_code_engine(_Settings("anthropic", auth_source="anthropic_api_key")) is False


def test_map_assistant_text_and_tool_use():
    msg = AssistantMessage(
        [
            TextBlock("hello "),
            ToolUseBlock("Read", {"path": "a.py"}),
        ]
    )
    events, session_id, usage, is_result = map_sdk_message_to_events(msg)
    assert session_id is None
    assert usage is None
    assert is_result is False
    assert isinstance(events[0], AssistantTextDelta)
    assert events[0].text == "hello "
    assert isinstance(events[1], ToolExecutionStarted)
    assert events[1].tool_name == "Read"
    assert events[1].tool_input == {"path": "a.py"}


def test_map_tool_result_and_final():
    user = UserMessage([ToolResultBlock("file contents")])
    events, _, _, is_result = map_sdk_message_to_events(user)
    assert is_result is False
    assert isinstance(events[0], ToolExecutionCompleted)
    assert "file contents" in events[0].output

    result = ResultMessage(
        session_id="sess-1",
        usage={"input_tokens": 3, "output_tokens": 5, "cache_read_input_tokens": 1},
        result="OK",
        is_error=False,
        subtype="success",
    )
    events, session_id, usage, is_result = map_sdk_message_to_events(result)
    assert is_result is True
    assert session_id == "sess-1"
    assert usage is not None
    assert usage.input_tokens == 4  # 3 + cache_read 1
    assert usage.output_tokens == 5
    assert isinstance(events[-1], AssistantTurnComplete)
    assert events[-1].message.text == "OK"


def test_map_result_error_without_text():
    result = ResultMessage(
        session_id=None,
        usage={},
        result="",
        is_error=True,
        subtype="error_during_execution",
    )
    events, _, _, is_result = map_sdk_message_to_events(result)
    assert is_result is True
    assert any(isinstance(e, ErrorEvent) for e in events)
