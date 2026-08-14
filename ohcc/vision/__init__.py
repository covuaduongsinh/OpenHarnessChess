"""Vision helpers re-exporting vision-board-mcp when on path."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_path() -> None:
    src = Path(__file__).resolve().parents[2] / "mcp-servers" / "vision-board-mcp" / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def analyze_board_image(*args, **kwargs):
    _ensure_path()
    from vision_board_mcp.board_vision import analyze_board_image as _fn

    return _fn(*args, **kwargs)
