"""PGN parse + replay tests."""

from __future__ import annotations

from pathlib import Path

from ohcc.chess_core.pgn import read_pgn_file, read_pgn_text, replay_game

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "data" / "sample-pgn" / "scholars_mate.pgn"


def test_parse_scholars_mate_file() -> None:
    games = read_pgn_file(SAMPLE)
    assert len(games) == 1
    g = games[0]
    assert g.white == "DemoWhite"
    assert g.moves[-1].startswith("Qxf7")
    assert len(g.moves) == 7


def test_replay_detects_check_and_mate() -> None:
    games = read_pgn_file(SAMPLE)
    plies = replay_game(games[0])
    assert plies[-1].is_mate or plies[-1].is_check
    assert plies[-1].is_capture
    assert "K" in plies[-1].fen_after or "k" in plies[-1].fen_after


def test_comments_and_ravs_stripped() -> None:
    text = """
[White "A"]
[Black "B"]

1. e4 {best} e5 (1... c5 2. Nf3) 2. Nf3 *
"""
    games = read_pgn_text(text)
    assert games[0].moves == ["e4", "e5", "Nf3"]
