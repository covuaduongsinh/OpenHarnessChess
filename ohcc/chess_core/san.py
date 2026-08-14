"""SAN parsing and application against a Board (MIT)."""

from __future__ import annotations

import re

from ohcc.chess_core.board import Board, is_white
from ohcc.chess_core.movegen import Move, apply_move, generate_legal_moves
from ohcc.chess_core.squares import file_of, rank_of, square_from_name, square_name

_SAN_CASTLE = re.compile(r"^(O-O-O|O-O|0-0-0|0-0)(\+|#)?$")
_SAN_MOVE = re.compile(
    r"^(?P<piece>[KQRBN])?"
    r"(?P<from_file>[a-h])?"
    r"(?P<from_rank>[1-8])?"
    r"(?P<capture>x)?"
    r"(?P<to>[a-h][1-8])"
    r"(?:=(?P<promo>[QRBN]))?"
    r"(?P<check>[+#])?$"
)


def normalize_san(san: str) -> str:
    """Strip annotation glyphs and normalize castling zeros."""
    s = san.strip()
    s = re.sub(r"[\!\?]+$", "", s)
    s = s.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    return s


def parse_san_move(board: Board, san: str) -> Move:
    """Resolve a SAN string to a legal Move on *board*."""
    san = normalize_san(san)
    castle = _SAN_CASTLE.match(san)
    if castle:
        token = castle.group(1).replace("0", "O")
        candidates = [m for m in generate_legal_moves(board) if m.is_castle]
        if token in ("O-O",):
            # King side: king moves two files toward h
            candidates = [m for m in candidates if file_of(m.to_sq) == 6]
        else:
            candidates = [m for m in candidates if file_of(m.to_sq) == 2]
        if len(candidates) != 1:
            raise ValueError(f"Cannot resolve castling SAN {san!r} in {board.fen()}")
        return candidates[0]

    # Pawn push without piece letter may be like e4, exd5, e8=Q
    m = _SAN_MOVE.match(san)
    if not m:
        # Try bare pawn form already covered; fail
        raise ValueError(f"Unrecognized SAN: {san!r}")

    piece_letter = m.group("piece") or "P"
    to_sq = square_from_name(m.group("to"))
    promo = m.group("promo")
    from_file = m.group("from_file")
    from_rank = m.group("from_rank")

    want_white = board.turn_white
    candidates: list[Move] = []
    for move in generate_legal_moves(board):
        piece = board.squares[move.from_sq]
        if piece is None:
            continue
        if piece.upper() != piece_letter:
            continue
        if is_white(piece) != want_white:
            continue
        if move.to_sq != to_sq:
            continue
        if promo:
            if not move.promotion or move.promotion.upper() != promo:
                continue
        elif move.promotion:
            # SAN without promo should not match promotion moves unless default;
            # require explicit promo in SAN for promotions.
            continue
        if from_file is not None and file_of(move.from_sq) != ord(from_file) - ord("a"):
            continue
        if from_rank is not None and rank_of(move.from_sq) != int(from_rank) - 1:
            continue
        candidates.append(move)

    if not candidates:
        raise ValueError(f"No legal move for SAN {san!r} in {board.fen()}")
    if len(candidates) > 1:
        # Prefer capture match if SAN has x
        if m.group("capture"):
            caps = [
                c
                for c in candidates
                if board.squares[c.to_sq] is not None or c.is_en_passant
            ]
            if len(caps) == 1:
                return caps[0]
        raise ValueError(
            f"Ambiguous SAN {san!r} matches {len(candidates)} moves in {board.fen()}"
        )
    return candidates[0]


def apply_san(board: Board, san: str) -> Board:
    """Apply a SAN move and return the new board."""
    return apply_move(board, parse_san_move(board, san))


def move_to_san(board: Board, move: Move) -> str:
    """Convert a legal move to SAN (subset used for diagnostics)."""
    piece = board.squares[move.from_sq]
    if piece is None:
        raise ValueError("empty from square")
    if move.is_castle:
        return "O-O" if file_of(move.to_sq) == 6 else "O-O-O"
    kind = piece.upper()
    dest = square_name(move.to_sq)
    capture = board.squares[move.to_sq] is not None or move.is_en_passant
    if kind == "P":
        san = ""
        if capture:
            san = f"{chr(ord('a') + file_of(move.from_sq))}x{dest}"
        else:
            san = dest
        if move.promotion:
            san += f"={move.promotion.upper()}"
    else:
        # Disambiguate
        others = [
            m
            for m in generate_legal_moves(board)
            if m is not move
            and board.squares[m.from_sq]
            and board.squares[m.from_sq].upper() == kind
            and m.to_sq == move.to_sq
            and m.promotion == move.promotion
        ]
        san = kind
        if others:
            same_file = any(file_of(o.from_sq) == file_of(move.from_sq) for o in others)
            same_rank = any(rank_of(o.from_sq) == rank_of(move.from_sq) for o in others)
            if not same_file:
                san += chr(ord("a") + file_of(move.from_sq))
            elif not same_rank:
                san += str(rank_of(move.from_sq) + 1)
            else:
                san += square_name(move.from_sq)
        if capture:
            san += "x"
        san += dest
        if move.promotion:
            san += f"={move.promotion.upper()}"
    nxt = apply_move(board, move)
    if nxt.in_check():
        # mate if no legal replies
        if not generate_legal_moves(nxt):
            san += "#"
        else:
            san += "+"
    return san
