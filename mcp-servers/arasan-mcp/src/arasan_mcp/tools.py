"""MCP tool metadata for Arasan analysis."""

from __future__ import annotations

TOOL_SPECS: list[dict] = [
    {
        "name": "analyze_fen",
        "description": (
            "Analyze a FEN with Arasan (MIT). Returns eval/PV for coach use only — "
            "do not dump raw scores or bestmove to preschool/primary students."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fen": {"type": "string"},
                "depth": {"type": "integer", "default": 12},
                "multipv": {"type": "integer", "default": 1},
            },
            "required": ["fen"],
        },
    },
    {
        "name": "evaluate_position",
        "description": "Quick evaluation of a FEN via Arasan (shallower depth).",
        "input_schema": {
            "type": "object",
            "properties": {
                "fen": {"type": "string"},
                "depth": {"type": "integer", "default": 8},
            },
            "required": ["fen"],
        },
    },
    {
        "name": "compare_positions",
        "description": (
            "Compare two FENs (before/after a move) and return the mover's eval drop "
            "in centipawns. Coach-internal signal for blunder/mistake detection."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fen_before": {"type": "string"},
                "fen_after": {"type": "string"},
                "mover_is_white": {"type": "boolean"},
                "depth": {"type": "integer", "default": 10},
            },
            "required": ["fen_before", "fen_after", "mover_is_white"],
        },
    },
]
