"""Puzzle domain model."""

from __future__ import annotations

from dataclasses import dataclass

from ohcc.scaffolding.bloom import BloomLevel


@dataclass
class Puzzle:
    """A single scaffolding exercise destined for the Obsidian vault."""

    title: str
    fen: str
    bloom: BloomLevel
    prompt: str
    source_pgn: str = ""
    student_level: str = "primary"
