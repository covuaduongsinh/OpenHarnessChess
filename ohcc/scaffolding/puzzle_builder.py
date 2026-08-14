"""ScaffoldingPuzzleBuilder — PGN → Bloom puzzles → Obsidian Markdown."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ohcc.chess_core.pgn import PgnGame, read_pgn_file, read_pgn_text, replay_game
from ohcc.models.puzzle import Puzzle
from ohcc.scaffolding.bloom import BLOOM_VAULT_DIRS, BloomLevel
from ohcc.scaffolding.markdown_export import render_puzzle_markdown, slugify, write_puzzle
from ohcc.scaffolding.mistake_detect import TeachingMoment, detect_teaching_moments
from ohcc.scaffolding.questions import questions_for_moment

if TYPE_CHECKING:
    from ohcc.engine.arasan import PositionEvaluator


@dataclass
class BuildResult:
    """Paths written for one build run."""

    written: list[Path] = field(default_factory=list)
    moments: list[TeachingMoment] = field(default_factory=list)
    games: int = 0
    used_arasan: bool = False


@dataclass
class ScaffoldingPuzzleBuilder:
    """Build scaffolding exercises from PGN games into an Obsidian vault."""

    vault_root: Path
    student_level: str = "primary"
    max_moments_per_game: int = 4
    arasan_mcp_enabled: bool = False
    arasan_path: str | Path | None = None
    eval_depth: int = 10
    evaluator: PositionEvaluator | None = None

    def build_from_pgn(self, pgn_path: Path) -> list[Path]:
        """Read a PGN file and write puzzle Markdown into the vault."""
        return self.build(pgn_path=pgn_path).written

    def build(
        self,
        *,
        pgn_path: Path | None = None,
        pgn_text: str | None = None,
        source_label: str = "",
    ) -> BuildResult:
        """Full pipeline: parse → replay → detect moments → Bloom MD export."""
        if pgn_path is not None:
            games = read_pgn_file(pgn_path)
            source = source_label or str(pgn_path.as_posix())
        elif pgn_text is not None:
            games = read_pgn_text(pgn_text)
            source = source_label or "inline.pgn"
        else:
            raise ValueError("Provide pgn_path or pgn_text")

        evaluator, owned = self._resolve_evaluator()
        result = BuildResult(games=len(games), used_arasan=evaluator is not None)
        try:
            for gi, game in enumerate(games, start=1):
                written, moments = self._build_game(
                    game, source=source, game_index=gi, evaluator=evaluator
                )
                result.written.extend(written)
                result.moments.extend(moments)
        finally:
            if owned and evaluator is not None:
                evaluator.close()
        return result

    def puzzles_for_moment(
        self,
        moment: TeachingMoment,
        *,
        source: str,
        game_label: str,
    ) -> list[Puzzle]:
        """Materialize three Bloom puzzles for one teaching moment."""
        prompts = questions_for_moment(moment, student_level=self.student_level)
        base_title = self._moment_title(moment, game_label)
        puzzles: list[Puzzle] = []
        for level, prompt in prompts.items():
            puzzles.append(
                Puzzle(
                    title=f"{base_title} — {self._bloom_vi(level)}",
                    fen=moment.fen,
                    bloom=level,
                    prompt=prompt,
                    source_pgn=source,
                    student_level=self.student_level,
                )
            )
        return puzzles

    def _resolve_evaluator(self) -> tuple[PositionEvaluator | None, bool]:
        if self.evaluator is not None:
            return self.evaluator, False
        if not self.arasan_mcp_enabled:
            return None, False
        try:
            from ohcc.engine.arasan import ArasanEvaluator

            return ArasanEvaluator(self.arasan_path, default_depth=self.eval_depth), True
        except Exception:
            return None, False

    def _build_game(
        self,
        game: PgnGame,
        *,
        source: str,
        game_index: int,
        evaluator: PositionEvaluator | None,
    ) -> tuple[list[Path], list[TeachingMoment]]:
        plies = replay_game(game)
        moments = detect_teaching_moments(
            plies,
            max_moments=self.max_moments_per_game,
            evaluator=evaluator,
            eval_depth=self.eval_depth,
        )
        game_label = f"{game.white}_vs_{game.black}"
        written: list[Path] = []
        for mi, moment in enumerate(moments, start=1):
            for puzzle in self.puzzles_for_moment(
                moment, source=source, game_label=game_label
            ):
                path = self._write_puzzle(
                    puzzle,
                    moment=moment,
                    game_index=game_index,
                    moment_index=mi,
                )
                written.append(path)
        return written, moments

    def _write_puzzle(
        self,
        puzzle: Puzzle,
        *,
        moment: TeachingMoment,
        game_index: int,
        moment_index: int,
    ) -> Path:
        rel_dir = BLOOM_VAULT_DIRS[puzzle.bloom]
        filename = (
            f"g{game_index:02d}-m{moment_index:02d}-ply{moment.ply.ply_index:02d}-"
            f"{slugify(moment.kind)}-{puzzle.bloom.value}.md"
        )
        path = self.vault_root / rel_dir / filename
        drop_note = f" | drop_cp={moment.drop_cp}" if moment.drop_cp is not None else ""
        teacher_note = (
            f"Moment: {moment.kind} | severity: {moment.severity} | "
            f"SAN played: {moment.ply.san} | {moment.note}{drop_note}"
        )
        content = render_puzzle_markdown(
            title=puzzle.title,
            fen=puzzle.fen,
            bloom=puzzle.bloom.value,
            prompt=puzzle.prompt,
            source_pgn=puzzle.source_pgn,
            student_level=puzzle.student_level,
            moment_kind=moment.kind,
            ply_index=moment.ply.ply_index,
            san=moment.ply.san,
            severity=moment.severity,
            teacher_note=teacher_note,
        )
        return write_puzzle(path, content)

    def _moment_title(self, moment: TeachingMoment, game_label: str) -> str:
        kind_vi = {
            "check": "Nước chiếu",
            "mate": "Chiếu hết",
            "capture": "Bắt quân",
            "hanging": "Quân treo",
            "eval_drop": "Nước sơ ý (eval)",
            "annotated": "Thời điểm dạy",
        }.get(moment.kind, moment.kind)
        return f"{kind_vi} (ply {moment.ply.ply_index}) — {game_label}"

    @staticmethod
    def _bloom_vi(level: BloomLevel) -> str:
        return {
            BloomLevel.REMEMBER: "Nhận biết",
            BloomLevel.APPLY: "Áp dụng",
            BloomLevel.ANALYZE: "Phân tích",
        }[level]
