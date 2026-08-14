"""UCI analysis result parsing and score helpers (MIT)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_INFO_SCORE_CP = re.compile(r"\bscore\s+cp\s+(-?\d+)")
_INFO_SCORE_MATE = re.compile(r"\bscore\s+mate\s+(-?\d+)")
_INFO_DEPTH = re.compile(r"\bdepth\s+(\d+)")
_INFO_PV = re.compile(r"\bpv\s+(.+)$")
_INFO_MULTIPV = re.compile(r"\bmultipv\s+(\d+)")


@dataclass
class AnalysisResult:
    """Engine analysis for coach use (do not dump raw scores to young students)."""

    fen: str
    depth: int = 0
    score_cp: int | None = None  # side-to-move centipawns (UCI convention)
    mate: int | None = None  # mate in N (side to move), negative if mated
    bestmove: str | None = None
    pv: list[str] = field(default_factory=list)
    multipv: int = 1
    raw_info: list[str] = field(default_factory=list)

    def white_relative_cp(self, *, white_to_move: bool) -> int | None:
        """Convert STM-relative score to White-relative centipawns."""
        if self.mate is not None:
            # Large magnitude mate scores for comparisons
            mate_cp = 100000 - abs(self.mate) * 100
            stm = mate_cp if self.mate > 0 else -mate_cp
            return stm if white_to_move else -stm
        if self.score_cp is None:
            return None
        return self.score_cp if white_to_move else -self.score_cp

    def as_dict(self) -> dict:
        return {
            "fen": self.fen,
            "depth": self.depth,
            "score_cp": self.score_cp,
            "mate": self.mate,
            "bestmove": self.bestmove,
            "pv": list(self.pv),
            "multipv": self.multipv,
            "note": (
                "Internal coach signal only. Do not show raw eval/bestmove "
                "to preschool/primary students; use Socratic questions."
            ),
        }


def parse_info_line(line: str, result: AnalysisResult) -> None:
    """Update *result* from a UCI ``info`` line (keeps deepest multipv 1)."""
    result.raw_info.append(line)
    multipv_m = _INFO_MULTIPV.search(line)
    multipv = int(multipv_m.group(1)) if multipv_m else 1
    depth_m = _INFO_DEPTH.search(line)
    depth = int(depth_m.group(1)) if depth_m else result.depth

    # Prefer multipv 1; accept higher depth for same multipv
    if multipv != 1 and result.score_cp is not None:
        return
    if depth < result.depth and result.score_cp is not None and multipv == result.multipv:
        return

    mate_m = _INFO_SCORE_MATE.search(line)
    cp_m = _INFO_SCORE_CP.search(line)
    if mate_m:
        result.mate = int(mate_m.group(1))
        result.score_cp = None
        result.depth = depth
        result.multipv = multipv
    elif cp_m:
        result.score_cp = int(cp_m.group(1))
        result.mate = None
        result.depth = depth
        result.multipv = multipv

    pv_m = _INFO_PV.search(line)
    if pv_m and multipv == 1:
        result.pv = pv_m.group(1).strip().split()


def parse_bestmove_line(line: str) -> str | None:
    """Extract bestmove token from a UCI bestmove line."""
    parts = line.strip().split()
    if len(parts) >= 2 and parts[0] == "bestmove":
        move = parts[1]
        return None if move == "(none)" else move
    return None


def mover_eval_drop_cp(
    *,
    before: AnalysisResult,
    after: AnalysisResult,
    mover_is_white: bool,
) -> int | None:
    """Positive value means the mover's position worsened (centipawns lost)."""
    before_w = before.white_relative_cp(white_to_move=mover_is_white)
    after_w = after.white_relative_cp(white_to_move=not mover_is_white)
    if before_w is None or after_w is None:
        return None
    mover_before = before_w if mover_is_white else -before_w
    mover_after = after_w if mover_is_white else -after_w
    return mover_before - mover_after
