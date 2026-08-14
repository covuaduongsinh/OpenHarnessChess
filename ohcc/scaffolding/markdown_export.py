"""Export puzzles to Obsidian-compatible Markdown."""

from __future__ import annotations

import re
from pathlib import Path


def render_puzzle_markdown(
    *,
    title: str,
    fen: str,
    bloom: str,
    prompt: str,
    source_pgn: str = "",
    student_level: str = "primary",
    moment_kind: str = "",
    ply_index: int | None = None,
    san: str = "",
    severity: str = "",
    teacher_note: str = "",
) -> str:
    """Render a single scaffolding puzzle note with YAML frontmatter."""
    tags = ["ohcc", "puzzle", f"bloom-{bloom}"]
    if moment_kind:
        tags.append(moment_kind)

    lines = [
        "---",
        "type: scaffolding-puzzle",
        f"bloom: {bloom}",
        f'fen: "{fen}"',
        f'source_pgn: "{_yaml_escape(source_pgn)}"',
        f"student_level: {student_level}",
    ]
    if moment_kind:
        lines.append(f"moment_kind: {moment_kind}")
    if ply_index is not None:
        lines.append(f"ply_index: {ply_index}")
    if san:
        lines.append(f'san: "{_yaml_escape(san)}"')
    if severity:
        lines.append(f"severity: {severity}")
    lines.append(f"tags: [{', '.join(tags)}]")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    lines.append("## Câu hỏi gợi mở (Socratic)")
    lines.append("")
    lines.append(prompt.strip())
    lines.append("")
    lines.append("## Bàn cờ (FEN)")
    lines.append("")
    lines.append(f"`{fen}`")
    lines.append("")
    if teacher_note:
        lines.append("## Ghi chú giáo viên")
        lines.append("")
        lines.append(teacher_note.strip())
        lines.append("")
        lines.append("> Không đọc nguyên si cho học viên. Không đưa nước đi giải ngay.")
        lines.append("")
    return "\n".join(lines)


def write_puzzle(path: Path, content: str) -> Path:
    """Write puzzle Markdown to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def slugify(text: str, *, max_len: int = 48) -> str:
    """Filesystem-friendly slug."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return (text or "puzzle")[:max_len]


def _yaml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
