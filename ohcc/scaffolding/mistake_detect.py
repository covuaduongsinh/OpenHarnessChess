"""Teaching-moment detection: heuristics + optional Arasan eval drops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ohcc.chess_core.heuristics.hanging import find_hanging_pieces
from ohcc.chess_core.pgn import ReplayPly

if TYPE_CHECKING:
    from ohcc.engine.arasan import PositionEvaluator


@dataclass(frozen=True)
class TeachingMoment:
    """A position worth turning into Bloom scaffolding puzzles."""

    ply: ReplayPly
    kind: str  # check | capture | hanging | mate | eval_drop | annotated
    fen: str  # position to show (usually fen_before for "what now?")
    severity: str  # tip | inaccuracy | mistake | blunder
    note: str = ""
    drop_cp: int | None = None


def classify_eval_drop(delta_cp: int) -> str:
    """Classify an evaluation drop in centipawns for the side that moved."""
    abs_delta = abs(delta_cp)
    if abs_delta >= 200:
        return "blunder"
    if abs_delta >= 100:
        return "mistake"
    if abs_delta >= 50:
        return "inaccuracy"
    return "ok"


def white_relative_cp(
    score_cp: int | None,
    mate: int | None,
    *,
    white_to_move: bool,
) -> int | None:
    """Convert STM-relative score to White-relative centipawns."""
    if mate is not None:
        mate_cp = 100000 - abs(mate) * 100
        stm = mate_cp if mate > 0 else -mate_cp
        return stm if white_to_move else -stm
    if score_cp is None:
        return None
    return score_cp if white_to_move else -score_cp


def mover_drop_cp(
    *,
    before_cp: int | None,
    before_mate: int | None,
    after_cp: int | None,
    after_mate: int | None,
    mover_is_white: bool,
) -> int | None:
    """Positive value = mover's position worsened (centipawns lost)."""
    before_w = white_relative_cp(before_cp, before_mate, white_to_move=mover_is_white)
    after_w = white_relative_cp(after_cp, after_mate, white_to_move=not mover_is_white)
    if before_w is None or after_w is None:
        return None
    mover_before = before_w if mover_is_white else -before_w
    mover_after = after_w if mover_is_white else -after_w
    return mover_before - mover_after


def detect_teaching_moments(
    plies: list[ReplayPly],
    *,
    max_moments: int = 6,
    include_captures: bool = True,
    evaluator: PositionEvaluator | None = None,
    eval_depth: int = 10,
    min_drop_cp: int = 50,
) -> list[TeachingMoment]:
    """Select pedagogical moments.

    Without *evaluator*: mate / check / hanging / capture heuristics.
    With *evaluator* (Arasan): also tag eval drops and upgrade severity.
    """
    moments: list[TeachingMoment] = []
    seen_fens: set[str] = set()

    eval_cache: dict[str, tuple[int | None, int | None]] = {}

    def _eval(fen: str) -> tuple[int | None, int | None]:
        if fen in eval_cache:
            return eval_cache[fen]
        if evaluator is None:
            return None, None
        snap = evaluator.evaluate(fen, depth=eval_depth)
        pair = (snap.score_cp, snap.mate)
        eval_cache[fen] = pair
        return pair

    for ply in plies:
        candidates: list[TeachingMoment] = []
        drop: int | None = None
        severity_from_eval = "ok"

        if evaluator is not None:
            b_cp, b_mate = _eval(ply.fen_before)
            a_cp, a_mate = _eval(ply.fen_after)
            drop = mover_drop_cp(
                before_cp=b_cp,
                before_mate=b_mate,
                after_cp=a_cp,
                after_mate=a_mate,
                mover_is_white=ply.side_moved_white,
            )
            if drop is not None and drop >= min_drop_cp:
                severity_from_eval = classify_eval_drop(drop)
                candidates.append(
                    TeachingMoment(
                        ply=ply,
                        kind="eval_drop",
                        fen=ply.fen_before,
                        severity=severity_from_eval,
                        note=f"Eval drop ~{drop}cp (Arasan, coach-internal)",
                        drop_cp=drop,
                    )
                )

        if ply.is_mate:
            candidates.append(
                TeachingMoment(
                    ply=ply,
                    kind="mate",
                    fen=ply.fen_before,
                    severity=_prefer_severity("tip", severity_from_eval),
                    note="Vị trí trước nước chiếu hết",
                    drop_cp=drop,
                )
            )
        elif ply.is_check:
            candidates.append(
                TeachingMoment(
                    ply=ply,
                    kind="check",
                    fen=ply.fen_before,
                    severity=_prefer_severity("tip", severity_from_eval),
                    note="Vị trí trước nước chiếu",
                    drop_cp=drop,
                )
            )

        hanging_after = find_hanging_pieces(
            ply.fen_after, for_side_white=ply.side_moved_white
        )
        if hanging_after:
            candidates.append(
                TeachingMoment(
                    ply=ply,
                    kind="hanging",
                    fen=ply.fen_after,
                    severity=_prefer_severity("mistake", severity_from_eval),
                    note=f"Quân treo: {', '.join(hanging_after)}",
                    drop_cp=drop,
                )
            )

        if include_captures and ply.is_capture and not ply.is_check:
            candidates.append(
                TeachingMoment(
                    ply=ply,
                    kind="capture",
                    fen=ply.fen_before,
                    severity=_prefer_severity("tip", severity_from_eval),
                    note="Vị trí trước nước bắt quân",
                    drop_cp=drop,
                )
            )

        for mom in candidates:
            key = f"{mom.kind}:{mom.fen}"
            if key in seen_fens:
                continue
            seen_fens.add(key)
            moments.append(mom)

    rank = {
        "blunder": -1,
        "mate": 0,
        "eval_drop": 1,
        "hanging": 2,
        "check": 3,
        "capture": 4,
        "annotated": 5,
    }
    severity_rank = {"blunder": 0, "mistake": 1, "inaccuracy": 2, "tip": 3, "ok": 4}

    def sort_key(m: TeachingMoment) -> tuple:
        return (
            severity_rank.get(m.severity, 9),
            rank.get(m.kind, 9),
            m.ply.ply_index,
        )

    moments.sort(key=sort_key)
    return moments[:max_moments]


def upgrade_moments_with_evaluator(
    moments: list[TeachingMoment],
    plies: list[ReplayPly],
    evaluator: PositionEvaluator,
    *,
    eval_depth: int = 10,
) -> list[TeachingMoment]:
    """Re-run detection with evaluator (convenience for builders)."""
    _ = moments
    return detect_teaching_moments(
        plies, evaluator=evaluator, eval_depth=eval_depth, max_moments=max(6, len(moments))
    )


def _prefer_severity(base: str, eval_severity: str) -> str:
    order = ["tip", "inaccuracy", "mistake", "blunder"]
    if eval_severity not in order:
        return base
    if base not in order:
        return eval_severity
    return eval_severity if order.index(eval_severity) > order.index(base) else base
