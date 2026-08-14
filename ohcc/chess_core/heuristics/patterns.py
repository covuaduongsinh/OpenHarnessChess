"""Tactical pattern catalogue for Socratic coaching (stub)."""

from __future__ import annotations

KNOWN_PATTERNS: tuple[str, ...] = (
    "hanging_piece",
    "simple_capture",
    "check",
    "fork_preview",
    "back_rank_hint",
)


def match_patterns(fen: str) -> list[str]:
    """Match teaching patterns on a FEN. Heuristic implementation comes later."""
    _ = fen
    return []
