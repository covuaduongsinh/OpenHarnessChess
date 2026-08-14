"""Load Thầy Tường system prompt and shared pedagogy anchors."""

from __future__ import annotations

from pathlib import Path

# Pedagogy anchors that must appear in both SSOT and runtime agent body.
REQUIRED_ANCHORS: tuple[str, ...] = (
    "Thầy Tường",
    "CLB Cờ vua Dương Sinh",
    "Socratic",
    "gợi mở",
    "Bloom",
    "Nhận biết",
    "Áp dụng",
    "Phân tích",
    "Không đưa nước đi",
    "eval thô",
    "Arasan",
    "Stockfish",
    "Maia",
    "thầy",
    "em",
)

MIN_PROMPT_CHARS = 1500

_PERSONA_REL = Path("ohcc") / "coach" / "personas" / "thay_tuong.md"
_AGENT_REL = Path("plugins") / "ohcc-coach" / "agents" / "coach-agent.md"


def repo_root() -> Path:
    """Return repository root (parent of the top-level ``ohcc`` package)."""
    return Path(__file__).resolve().parents[2]


def persona_path() -> Path:
    return repo_root() / _PERSONA_REL


def agent_path() -> Path:
    return repo_root() / _AGENT_REL


def load_thay_tuong_prompt() -> str:
    """Load the SSOT system prompt for Thầy Tường."""
    path = persona_path()
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Empty persona prompt: {path}")
    return text


def load_coach_agent_markdown() -> str:
    """Load the full coach-agent plugin markdown (frontmatter + body)."""
    path = agent_path()
    return path.read_text(encoding="utf-8")


def extract_agent_body(markdown: str | None = None) -> str:
    """Return the system_prompt body of coach-agent.md (after YAML frontmatter)."""
    content = markdown if markdown is not None else load_coach_agent_markdown()
    if not content.startswith("---"):
        return content.strip()
    rest = content[3:]
    end = rest.find("\n---")
    if end == -1:
        return content.strip()
    body = rest[end + len("\n---") :].lstrip("\n")
    return body.strip()


def missing_anchors(text: str, anchors: tuple[str, ...] = REQUIRED_ANCHORS) -> list[str]:
    """Return anchors not found in *text*."""
    return [a for a in anchors if a not in text]
