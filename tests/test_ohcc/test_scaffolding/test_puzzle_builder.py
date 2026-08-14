"""ScaffoldingPuzzleBuilder end-to-end tests."""

from __future__ import annotations

from pathlib import Path

from ohcc.scaffolding.mistake_detect import detect_teaching_moments
from ohcc.scaffolding.puzzle_builder import ScaffoldingPuzzleBuilder
from ohcc.chess_core.pgn import read_pgn_file, replay_game

ROOT = Path(__file__).resolve().parents[3]
SCHOLAR = ROOT / "data" / "sample-pgn" / "scholars_mate.pgn"
ITALIAN = ROOT / "data" / "sample-pgn" / "italian_capture.pgn"


def test_detect_moments_on_scholars_mate() -> None:
    game = read_pgn_file(SCHOLAR)[0]
    plies = replay_game(game)
    moments = detect_teaching_moments(plies, max_moments=6)
    assert moments
    kinds = {m.kind for m in moments}
    assert kinds & {"check", "mate", "capture", "hanging"}


def test_builder_writes_bloom_markdown(tmp_path: Path) -> None:
    # Minimal vault layout
    for sub in (
        "03-puzzles/bloom-remember",
        "03-puzzles/bloom-apply",
        "03-puzzles/bloom-analyze",
    ):
        (tmp_path / sub).mkdir(parents=True)

    builder = ScaffoldingPuzzleBuilder(
        vault_root=tmp_path,
        student_level="primary",
        max_moments_per_game=2,
    )
    result = builder.build(pgn_path=SCHOLAR)
    assert result.games == 1
    assert result.moments
    # 3 bloom levels per moment
    assert len(result.written) == len(result.moments) * 3

    for path in result.written:
        text = path.read_text(encoding="utf-8")
        assert "type: scaffolding-puzzle" in text
        assert "fen:" in text
        assert "bloom:" in text
        assert "Câu hỏi gợi mở" in text
        assert "Ghi chú giáo viên" in text
        # Socratic: no instant best-move dump as student prompt header
        assert "Nước tốt nhất" not in text.split("## Câu hỏi")[1].split("##")[0]

    blooms = {p.parent.name for p in result.written}
    assert "bloom-remember" in blooms
    assert "bloom-apply" in blooms
    assert "bloom-analyze" in blooms


def test_builder_italian_has_capture_or_check_moments(tmp_path: Path) -> None:
    for sub in (
        "03-puzzles/bloom-remember",
        "03-puzzles/bloom-apply",
        "03-puzzles/bloom-analyze",
    ):
        (tmp_path / sub).mkdir(parents=True)

    builder = ScaffoldingPuzzleBuilder(vault_root=tmp_path, max_moments_per_game=5)
    result = builder.build(pgn_path=ITALIAN)
    assert result.written
    assert any(m.kind in {"capture", "check", "hanging"} for m in result.moments)


def test_build_from_pgn_api(tmp_path: Path) -> None:
    for sub in (
        "03-puzzles/bloom-remember",
        "03-puzzles/bloom-apply",
        "03-puzzles/bloom-analyze",
    ):
        (tmp_path / sub).mkdir(parents=True)
    paths = ScaffoldingPuzzleBuilder(vault_root=tmp_path).build_from_pgn(SCHOLAR)
    assert paths
