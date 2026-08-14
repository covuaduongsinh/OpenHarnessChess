"""Student profile schema stubs (implemented with scaffolding pipeline)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StudentWeakness:
    """A recurring weakness observed across games."""

    tag: str
    description: str = ""
    frequency: int = 1


@dataclass
class StudentProfile:
    """Minimal student memory model; vault Markdown is the durable store."""

    student_id: str
    display_name: str
    level: str = "primary"  # preschool | primary
    weaknesses: list[StudentWeakness] = field(default_factory=list)
    notes: str = ""
