"""vision-board-mcp unit tests."""

from __future__ import annotations

from pathlib import Path

from vision_board_mcp.board_vision import analyze_board_image, validate_fen

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_validate_fen_start() -> None:
    ok, msg = validate_fen(START)
    assert ok
    assert msg == "ok"


def test_validate_fen_bad_rank() -> None:
    ok, _ = validate_fen("8/8/8/8/8/8/8/7 w - - 0 1")
    assert not ok


def test_analyze_with_fen_hint(tmp_path: Path) -> None:
    img = tmp_path / "board.png"
    # Minimal PNG header bytes are enough for "file exists" path; suffix matters
    img.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        + b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        + b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xb4"
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    inbox = tmp_path / "00-inbox"
    result = analyze_board_image(img, fen_hint=START, vault_inbox=inbox)
    assert result.ok
    assert result.fen is not None
    assert result.fen.startswith("rnbqkbnr/")
    assert result.source == "fen_hint"
    assert result.inbox_note
    assert Path(result.inbox_note).is_file()


def test_analyze_without_hint_pending(tmp_path: Path) -> None:
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"fake-jpeg")
    inbox = tmp_path / "inbox"
    result = analyze_board_image(img, vault_inbox=inbox)
    assert not result.ok
    assert result.source == "pending_review"
    assert result.inbox_note
