"""Load/save student profiles from the Obsidian vault (stub)."""

from __future__ import annotations

from pathlib import Path

from ohcc.coach.memory.schema import StudentProfile


def profile_path(vault_root: Path, student_id: str) -> Path:
    """Return the expected Markdown path for a student profile."""
    return vault_root / "01-students" / f"{student_id}.md"


def load_student_profile(vault_root: Path, student_id: str) -> StudentProfile | None:
    """Load a student profile from vault. Not implemented in Step 1 scaffold."""
    path = profile_path(vault_root, student_id)
    if not path.exists():
        return None
    raise NotImplementedError("Student profile loader lands with Step 2/3 wiring.")


def save_student_profile(vault_root: Path, profile: StudentProfile) -> Path:
    """Persist a student profile. Not implemented in Step 1 scaffold."""
    raise NotImplementedError("Student profile saver lands with Step 2/3 wiring.")
