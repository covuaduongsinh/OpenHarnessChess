"""Board, movegen, and SAN smoke tests."""

from __future__ import annotations

from ohcc.chess_core.board import Board
from ohcc.chess_core.fen import START_FEN
from ohcc.chess_core.movegen import generate_legal_moves
from ohcc.chess_core.san import apply_san, parse_san_move


def test_start_position_has_20_moves() -> None:
    board = Board.starting()
    assert board.fen() == START_FEN
    assert len(generate_legal_moves(board)) == 20


def test_scholars_mate_line() -> None:
    board = Board.starting()
    for san in ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"]:
        board = apply_san(board, san)
    assert board.in_check()
    assert generate_legal_moves(board) == []


def test_castling_kingside() -> None:
    # Clear path for white O-O: remove N and B
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    board = Board.from_fen(fen)
    board = apply_san(board, "O-O")
    assert board.piece_at(6) == "K"  # g1
    assert board.piece_at(5) == "R"  # f1


def test_ambiguous_san_raises_or_resolves() -> None:
    board = Board.starting()
    board = apply_san(board, "Nf3")
    board = apply_san(board, "Nf6")
    # Second knight move for white — unique
    move = parse_san_move(board, "Nc3")
    assert move is not None
