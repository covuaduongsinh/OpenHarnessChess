"""Eval-drop teaching moments with a fake evaluator."""

from __future__ import annotations

from ohcc.chess_core.pgn import ReplayPly
from ohcc.engine.arasan import CallableEvaluator, EvalSnapshot
from ohcc.scaffolding.mistake_detect import (
    classify_eval_drop,
    detect_teaching_moments,
    mover_drop_cp,
)
from ohcc.scaffolding.puzzle_builder import ScaffoldingPuzzleBuilder
from pathlib import Path


def test_classify_eval_drop_thresholds() -> None:
    assert classify_eval_drop(40) == "ok"
    assert classify_eval_drop(50) == "inaccuracy"
    assert classify_eval_drop(100) == "mistake"
    assert classify_eval_drop(200) == "blunder"


def test_mover_drop_math() -> None:
    # White to move +100; after black to move +80 (STM) => white -80; drop 180
    drop = mover_drop_cp(
        before_cp=100,
        before_mate=None,
        after_cp=80,
        after_mate=None,
        mover_is_white=True,
    )
    assert drop == 180


def test_detect_eval_drop_moment() -> None:
    fen_before = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    fen_after = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    scores = {
        fen_before: (150, None),  # white to move, good
        fen_after: (120, None),  # black to move +120 => white -120; drop 270
    }

    def fn(fen: str) -> EvalSnapshot:
        cp, mate = scores[fen]
        return EvalSnapshot(fen=fen, score_cp=cp, mate=mate, depth=8)

    plies = [
        ReplayPly(
            ply_index=1,
            san="e4",
            fen_before=fen_before,
            fen_after=fen_after,
            is_capture=False,
            is_check=False,
            is_mate=False,
            side_moved_white=True,
        )
    ]
    moments = detect_teaching_moments(
        plies,
        evaluator=CallableEvaluator(fn),
        include_captures=False,
        max_moments=5,
    )
    kinds = {m.kind for m in moments}
    assert "eval_drop" in kinds
    drop_m = next(m for m in moments if m.kind == "eval_drop")
    assert drop_m.severity == "blunder"
    assert drop_m.drop_cp == 270


def test_builder_with_injected_evaluator(tmp_path: Path) -> None:
    for sub in (
        "03-puzzles/bloom-remember",
        "03-puzzles/bloom-apply",
        "03-puzzles/bloom-analyze",
    ):
        (tmp_path / sub).mkdir(parents=True)

    # Always report a large drop for any fen
    def fn(fen: str) -> EvalSnapshot:
        # STM score depends on side: encode via " w " / " b "
        if " w " in fen:
            return EvalSnapshot(fen=fen, score_cp=200, mate=None, depth=6)
        return EvalSnapshot(fen=fen, score_cp=200, mate=None, depth=6)

    root = Path(__file__).resolve().parents[3]
    pgn = root / "data" / "sample-pgn" / "italian_capture.pgn"
    builder = ScaffoldingPuzzleBuilder(
        vault_root=tmp_path,
        max_moments_per_game=3,
        evaluator=CallableEvaluator(fn),
    )
    result = builder.build(pgn_path=pgn)
    assert result.used_arasan
    assert result.written
    # At least one moment should carry drop_cp when evaluator present
    assert any(m.drop_cp is not None for m in result.moments)
