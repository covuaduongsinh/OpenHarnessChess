"""Detect hanging / unprotected pieces (MIT heuristics)."""

from __future__ import annotations

from ohcc.chess_core.board import Board, is_white
from ohcc.chess_core.squares import square_name


def find_hanging_pieces(fen: str, *, for_side_white: bool | None = None) -> list[str]:
    """Return square names of pieces that are attacked and not defended.

    If *for_side_white* is None, check the side to move's pieces.
    """
    board = Board.from_fen(fen)
    side_white = board.turn_white if for_side_white is None else for_side_white
    hanging: list[str] = []
    for sq, piece in enumerate(board.squares):
        if piece is None:
            continue
        if is_white(piece) != side_white:
            continue
        if piece.upper() == "K":
            continue
        attacked = board.is_square_attacked(sq, by_white=not side_white)
        defended = board.is_square_attacked(sq, by_white=side_white)
        if attacked and not defended:
            hanging.append(square_name(sq))
    return hanging


def count_threatened_pieces(fen: str, *, for_side_white: bool | None = None) -> int:
    """Count pieces of a side that are currently attacked (defended or not)."""
    board = Board.from_fen(fen)
    side_white = board.turn_white if for_side_white is None else for_side_white
    count = 0
    for sq, piece in enumerate(board.squares):
        if piece is None or is_white(piece) != side_white:
            continue
        if piece.upper() == "K":
            continue
        if board.is_square_attacked(sq, by_white=not side_white):
            count += 1
    return count
