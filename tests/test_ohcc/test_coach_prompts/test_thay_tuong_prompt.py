"""Structural tests for Thầy Tường system prompt (Step 2)."""

from __future__ import annotations

import re

from ohcc.coach.persona_loader import (
    MIN_PROMPT_CHARS,
    REQUIRED_ANCHORS,
    extract_agent_body,
    load_coach_agent_markdown,
    load_thay_tuong_prompt,
    missing_anchors,
)
from ohcc.coach.socratic import BLOOM_QUESTION_STEMS, build_opening_question, sample_questions
from ohcc.scaffolding.bloom import BloomLevel


def test_load_thay_tuong_prompt_non_empty() -> None:
    prompt = load_thay_tuong_prompt()
    assert len(prompt) >= MIN_PROMPT_CHARS


def test_ssot_contains_required_anchors() -> None:
    prompt = load_thay_tuong_prompt()
    assert missing_anchors(prompt) == []


def test_agent_frontmatter_and_body() -> None:
    raw = load_coach_agent_markdown()
    assert raw.startswith("---")
    assert re.search(r"(?m)^name:\s*coach-agent\s*$", raw)
    assert "scaffolding-puzzle-builder" in raw
    assert "socratic-game-analysis" in raw
    assert "student-memory" in raw
    assert "requiredMcpServers" in raw or "arasan" in raw
    assert "criticalSystemReminder" in raw

    body = extract_agent_body(raw)
    assert len(body) >= MIN_PROMPT_CHARS
    assert missing_anchors(body) == []


def test_ssot_and_agent_body_share_anchors() -> None:
    """Both sources must carry the same pedagogy anchors (sync check)."""
    ssot = load_thay_tuong_prompt()
    body = extract_agent_body()
    for anchor in REQUIRED_ANCHORS:
        assert anchor in ssot
        assert anchor in body


def test_hard_rules_anti_spoiler_language() -> None:
    prompt = load_thay_tuong_prompt().lower()
    assert "không đưa nước đi" in prompt
    assert "eval thô" in prompt
    assert "socratic" in prompt


def test_socratic_helpers_by_bloom() -> None:
    q = build_opening_question(bloom_level="remember", theme="quân treo")
    assert "bảo vệ" in q.lower() or "Quân" in q
    assert "quân treo" in q
    assert len(sample_questions(BloomLevel.APPLY)) >= 1
    assert set(BLOOM_QUESTION_STEMS) == {
        BloomLevel.REMEMBER,
        BloomLevel.APPLY,
        BloomLevel.ANALYZE,
    }
