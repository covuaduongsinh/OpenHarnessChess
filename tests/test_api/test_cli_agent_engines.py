"""Unit tests for Codex / Grok / Antigravity CLI event mappers."""

from __future__ import annotations

from types import SimpleNamespace

from openharness.api.antigravity_cli_engine import map_agy_json_line, uses_antigravity_cli_engine
from openharness.api.codex_cli_engine import map_codex_json_line, uses_codex_cli_engine
from openharness.api.grok_cli_engine import map_grok_json_line, uses_grok_cli_engine
from openharness.engine.stream_events import AssistantTextDelta, ErrorEvent


class _Settings:
    def __init__(self, provider: str, auth_source: str = ""):
        self.provider = provider
        self._auth_source = auth_source

    def resolve_profile(self):
        return "p", SimpleNamespace(auth_source=self._auth_source, api_format="")


def test_uses_flags():
    assert uses_codex_cli_engine(_Settings("openai_codex")) is True
    assert uses_grok_cli_engine(_Settings("grok")) is True
    assert uses_antigravity_cli_engine(_Settings("antigravity")) is True
    assert uses_codex_cli_engine(_Settings("anthropic", "anthropic_api_key")) is False


def test_map_grok_text():
    events = map_grok_json_line('{"type":"text","data":"OK"}')
    assert len(events) == 1
    assert isinstance(events[0], AssistantTextDelta)
    assert events[0].text == "OK"


def test_map_agy_text_delta():
    line = (
        '{"event":"step_update","step_update":{"step_type":"agent_response",'
        '"text_delta":"OK\\n","state":"DONE"}}'
    )
    events = map_agy_json_line(line)
    assert any(isinstance(e, AssistantTextDelta) and "OK" in e.text for e in events)


def test_map_codex_agent_message():
    events = map_codex_json_line('{"type":"agent_message","text":"hello"}')
    assert isinstance(events[0], AssistantTextDelta)
    assert events[0].text == "hello"


def test_map_codex_error():
    events = map_codex_json_line('{"type":"error","message":"boom"}')
    assert isinstance(events[0], ErrorEvent)
