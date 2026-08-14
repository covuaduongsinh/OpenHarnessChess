"""Minimal UCI-speaking fake engine for tests (not Arasan; protocol only)."""

from __future__ import annotations

import sys


def main() -> int:
    # Deterministic scores by FEN fragment for tests
    current_fen = "startpos"
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        if line == "uci":
            print("id name FakeUCI", flush=True)
            print("id author OHCC Tests", flush=True)
            print("uciok", flush=True)
        elif line == "isready":
            print("readyok", flush=True)
        elif line == "ucinewgame":
            continue
        elif line.startswith("position fen "):
            current_fen = line[len("position fen ") :].strip()
        elif line.startswith("position startpos"):
            current_fen = "startpos"
        elif line.startswith("go"):
            score = _score_for_fen(current_fen)
            print(f"info depth 8 score cp {score} pv e2e4", flush=True)
            print(f"info depth 10 score cp {score} pv e2e4 e7e5", flush=True)
            print("bestmove e2e4", flush=True)
        elif line.startswith("setoption"):
            continue
        elif line == "quit":
            return 0
    return 0


def _score_for_fen(fen: str) -> int:
    """Map FENs used in tests to fixed STM-relative scores."""
    # Markers embedded in tests via unique piece placements / move clocks
    if "drop_before" in fen:
        return 100
    if "drop_after" in fen:
        return -150
    # Use halfmove clock field if present as encoded score (hack for unit tests)
    parts = fen.split()
    if len(parts) >= 5 and parts[4].startswith("s"):
        try:
            return int(parts[4][1:])
        except ValueError:
            pass
    if fen == "startpos" or fen.startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"):
        return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
