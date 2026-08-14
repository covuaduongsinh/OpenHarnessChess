"""FEN helper smoke tests."""

from ohcc.chess_core.fen import START_FEN, side_to_move, split_fen


def test_start_fen_side_to_move() -> None:
    assert side_to_move(START_FEN) == "w"


def test_split_fen_fields() -> None:
    parts = split_fen(START_FEN)
    assert len(parts) >= 4
    assert parts[0].count("/") == 7
