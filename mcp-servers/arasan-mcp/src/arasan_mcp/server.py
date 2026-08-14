"""MCP stdio server wrapping Arasan UCI (MIT)."""

from __future__ import annotations

import atexit
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from arasan_mcp.analysis import mover_eval_drop_cp
from arasan_mcp.uci_client import UciClient, UciError, resolve_engine_path

server = FastMCP(
    "arasan-mcp",
    instructions=(
        "Arasan chess engine MCP (MIT License). "
        "Scores and bestmoves are internal coach signals for Thầy Tường. "
        "Never present raw eval or solution moves to young students; use Socratic questions."
    ),
)

_client: UciClient | None = None


def get_client() -> UciClient:
    """Lazy-start shared UCI client."""
    global _client
    if _client is None:
        path = os.environ.get("ARASAN_PATH")
        _client = UciClient.from_env(path)
        _client.start()
        atexit.register(_shutdown_client)
    return _client


def _shutdown_client() -> None:
    global _client
    if _client is not None:
        _client.stop()
        _client = None


@server.tool()
def analyze_fen(fen: str, depth: int = 12, multipv: int = 1) -> dict[str, Any]:
    """Analyze a FEN with Arasan. Coach-internal only."""
    try:
        result = get_client().analyze_fen(fen, depth=depth, multipv=max(1, multipv))
        return result.as_dict()
    except UciError as exc:
        return {"error": str(exc), "fen": fen}


@server.tool()
def evaluate_position(fen: str, depth: int = 8) -> dict[str, Any]:
    """Quick evaluation of a FEN."""
    try:
        result = get_client().evaluate_position(fen, depth=depth)
        return result.as_dict()
    except UciError as exc:
        return {"error": str(exc), "fen": fen}


@server.tool()
def compare_positions(
    fen_before: str,
    fen_after: str,
    mover_is_white: bool,
    depth: int = 10,
) -> dict[str, Any]:
    """Return mover eval drop (positive = position worsened for the mover)."""
    try:
        client = get_client()
        before = client.evaluate_position(fen_before, depth=depth)
        after = client.evaluate_position(fen_after, depth=depth)
        drop = mover_eval_drop_cp(before=before, after=after, mover_is_white=mover_is_white)
        severity = "ok"
        if drop is not None:
            if drop >= 200:
                severity = "blunder"
            elif drop >= 100:
                severity = "mistake"
            elif drop >= 50:
                severity = "inaccuracy"
        return {
            "fen_before": fen_before,
            "fen_after": fen_after,
            "mover_is_white": mover_is_white,
            "drop_cp": drop,
            "severity": severity,
            "before": before.as_dict(),
            "after": after.as_dict(),
            "note": "Internal coach signal only — use Socratic framing for students.",
        }
    except UciError as exc:
        return {"error": str(exc)}


def main() -> None:
    """Start the arasan-mcp stdio server."""
    # Fail fast with a clear message if binary missing (unless dry tests mock later)
    try:
        resolve_engine_path(os.environ.get("ARASAN_PATH"))
    except UciError as exc:
        # Still start MCP so clients see tool errors; log to stderr
        import sys

        print(f"arasan-mcp warning: {exc}", file=sys.stderr)
    server.run("stdio")


if __name__ == "__main__":
    main()
