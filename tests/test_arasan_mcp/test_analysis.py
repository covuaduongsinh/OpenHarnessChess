"""Unit tests for UCI analysis parsing and eval drop math."""

from __future__ import annotations

from arasan_mcp.analysis import (
    AnalysisResult,
    mover_eval_drop_cp,
    parse_bestmove_line,
    parse_info_line,
)


def test_parse_info_cp_and_pv() -> None:
    result = AnalysisResult(fen="start")
    parse_info_line("info depth 12 score cp 34 pv e2e4 e7e5 g1f3", result)
    assert result.depth == 12
    assert result.score_cp == 34
    assert result.pv[:2] == ["e2e4", "e7e5"]
    assert result.mate is None


def test_parse_info_mate() -> None:
    result = AnalysisResult(fen="start")
    parse_info_line("info depth 5 score mate 2 pv e2e4", result)
    assert result.mate == 2
    assert result.score_cp is None


def test_parse_bestmove() -> None:
    assert parse_bestmove_line("bestmove e2e4 ponder e7e5") == "e2e4"
    assert parse_bestmove_line("bestmove (none)") is None


def test_white_relative_and_mover_drop() -> None:
    before = AnalysisResult(fen="b", score_cp=100)  # white to move, +100
    after = AnalysisResult(fen="a", score_cp=50)  # black to move, +50 for black => -50 white
    # White moved: before +100 white, after -50 white => drop 150
    drop = mover_eval_drop_cp(before=before, after=after, mover_is_white=True)
    assert drop == 150

    # Black moved into better for black: before black STM +20 => white -20
    # after white STM +80 => white +80; black scores: before +20, after -80 => drop 100
    before_b = AnalysisResult(fen="b", score_cp=20)
    after_b = AnalysisResult(fen="a", score_cp=80)
    drop_b = mover_eval_drop_cp(before=before_b, after=after_b, mover_is_white=False)
    assert drop_b == 100
