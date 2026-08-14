"""MCP stdio server for chessboard photos (Zalo/Telegram intake)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from vision_board_mcp.board_vision import analyze_board_image, validate_fen

server = FastMCP(
    "vision-board-mcp",
    instructions=(
        "Chessboard photo → FEN helper for OHCC (MIT). "
        "Prefer fen_hint from teacher when auto-vision is unavailable. "
        "Writes review notes to vault/00-inbox."
    ),
)


def _default_inbox() -> Path | None:
    raw = os.environ.get("OHCC_VAULT") or os.environ.get("OHCC_VAULT_PATH")
    if raw:
        return Path(raw) / "00-inbox"
    # monorepo default
    root = Path.cwd()
    candidate = root / "vault" / "00-inbox"
    return candidate if candidate.parent.is_dir() else None


@server.tool()
def analyze_board_image_tool(
    image_path: str,
    fen_hint: str | None = None,
    side_hint: str | None = None,
    vault_inbox: str | None = None,
) -> dict[str, Any]:
    """Analyze a board photo. Provide fen_hint when possible for confirmed FEN."""
    inbox = Path(vault_inbox) if vault_inbox else _default_inbox()
    result = analyze_board_image(
        image_path,
        fen_hint=fen_hint,
        vault_inbox=inbox,
        side_hint=side_hint,
    )
    return result.as_dict()


@server.tool()
def validate_fen_tool(fen: str) -> dict[str, Any]:
    """Validate a FEN string (MIT, no python-chess)."""
    ok, message = validate_fen(fen)
    return {"ok": ok, "message": message, "fen": fen.strip()}


@server.tool()
def list_inbox_reviews(vault_inbox: str | None = None, limit: int = 20) -> dict[str, Any]:
    """List recent board-photo review notes in the vault inbox."""
    inbox = Path(vault_inbox) if vault_inbox else _default_inbox()
    if inbox is None or not inbox.is_dir():
        return {"ok": False, "reviews": [], "message": "Inbox not found"}
    notes = sorted(inbox.glob("board-photo-*.md"), reverse=True)[: max(1, limit)]
    return {
        "ok": True,
        "reviews": [{"path": str(p), "name": p.name} for p in notes],
        "inbox": str(inbox),
    }


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
