"""Legal move generation (MIT, no python-chess)."""

from __future__ import annotations

from dataclasses import dataclass

from ohcc.chess_core.board import Board, is_white, same_color
from ohcc.chess_core.squares import file_of, rank_of, square_at, square_name


@dataclass(frozen=True)
class Move:
    """A legal move on the board."""

    from_sq: int
    to_sq: int
    promotion: str | None = None  # uppercase piece letter Q/R/B/N
    is_castle: bool = False
    is_en_passant: bool = False

    def uci(self) -> str:
        promo = self.promotion.lower() if self.promotion else ""
        return f"{square_name(self.from_sq)}{square_name(self.to_sq)}{promo}"


def generate_legal_moves(board: Board) -> list[Move]:
    """Generate all legal moves for the side to move."""
    moves: list[Move] = []
    for sq, piece in enumerate(board.squares):
        if piece is None:
            continue
        if is_white(piece) != board.turn_white:
            continue
        moves.extend(_piece_moves(board, sq, piece))
    legal: list[Move] = []
    for move in moves:
        if _is_legal(board, move):
            legal.append(move)
    return legal


def apply_move(board: Board, move: Move) -> Board:
    """Return a new board with *move* applied."""
    b = board.copy()
    piece = b.squares[move.from_sq]
    if piece is None:
        raise ValueError(f"No piece on from-square {square_name(move.from_sq)}")

    captured = b.squares[move.to_sq]
    if move.is_en_passant:
        cap_sq = move.to_sq + (-8 if b.turn_white else 8)
        captured = b.squares[cap_sq]
        b.squares[cap_sq] = None

    # Castling rights updates
    b.clear_castling_for_square(move.from_sq)
    b.clear_castling_for_square(move.to_sq)

    # Execute move
    b.squares[move.to_sq] = piece
    b.squares[move.from_sq] = None

    if move.is_castle:
        if move.to_sq == 6:  # white O-O
            b.squares[5] = b.squares[7]
            b.squares[7] = None
        elif move.to_sq == 2:  # white O-O-O
            b.squares[3] = b.squares[0]
            b.squares[0] = None
        elif move.to_sq == 62:  # black O-O
            b.squares[61] = b.squares[63]
            b.squares[63] = None
        elif move.to_sq == 58:  # black O-O-O
            b.squares[59] = b.squares[56]
            b.squares[56] = None

    if move.promotion:
        promo = move.promotion.upper() if b.turn_white else move.promotion.lower()
        b.squares[move.to_sq] = promo

    # En passant target
    b.ep_square = None
    if piece.upper() == "P" and abs(move.to_sq - move.from_sq) == 16:
        b.ep_square = (move.from_sq + move.to_sq) // 2

    # Clocks
    if piece.upper() == "P" or captured is not None or move.is_en_passant:
        b.halfmove = 0
    else:
        b.halfmove += 1
    if not b.turn_white:
        b.fullmove += 1
    b.turn_white = not b.turn_white
    return b


def _is_legal(board: Board, move: Move) -> bool:
    nxt = apply_move(board, move)
    # Side that just moved must not leave their king in check
    return not nxt.in_check(white=board.turn_white)


def _piece_moves(board: Board, sq: int, piece: str) -> list[Move]:
    kind = piece.upper()
    if kind == "P":
        return _pawn_moves(board, sq, piece)
    if kind == "N":
        return _knight_moves(board, sq, piece)
    if kind == "B":
        return _slide_moves(board, sq, piece, ((1, 1), (1, -1), (-1, 1), (-1, -1)))
    if kind == "R":
        return _slide_moves(board, sq, piece, ((1, 0), (-1, 0), (0, 1), (0, -1)))
    if kind == "Q":
        return _slide_moves(
            board,
            sq,
            piece,
            ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)),
        )
    if kind == "K":
        return _king_moves(board, sq, piece)
    return []


def _pawn_moves(board: Board, sq: int, piece: str) -> list[Move]:
    white = is_white(piece)
    direction = 8 if white else -8
    start_rank = 1 if white else 6
    promo_rank = 7 if white else 0
    moves: list[Move] = []
    one = sq + direction
    if 0 <= one <= 63 and board.squares[one] is None:
        if rank_of(one) == promo_rank:
            for p in "QRBN":
                moves.append(Move(sq, one, promotion=p))
        else:
            moves.append(Move(sq, one))
            if rank_of(sq) == start_rank:
                two = sq + 2 * direction
                if board.squares[two] is None:
                    moves.append(Move(sq, two))
    for df in (-1, 1):
        f = file_of(sq) + df
        r = rank_of(sq) + (1 if white else -1)
        if not (0 <= f <= 7 and 0 <= r <= 7):
            continue
        to = square_at(f, r)
        target = board.squares[to]
        if target is not None and not same_color(piece, target):
            if r == promo_rank:
                for p in "QRBN":
                    moves.append(Move(sq, to, promotion=p))
            else:
                moves.append(Move(sq, to))
        elif board.ep_square == to:
            moves.append(Move(sq, to, is_en_passant=True))
    return moves


def _knight_moves(board: Board, sq: int, piece: str) -> list[Move]:
    moves: list[Move] = []
    for df, dr in (
        (1, 2),
        (2, 1),
        (-1, 2),
        (-2, 1),
        (1, -2),
        (2, -1),
        (-1, -2),
        (-2, -1),
    ):
        f, r = file_of(sq) + df, rank_of(sq) + dr
        if not (0 <= f <= 7 and 0 <= r <= 7):
            continue
        to = square_at(f, r)
        target = board.squares[to]
        if target is None or not same_color(piece, target):
            moves.append(Move(sq, to))
    return moves


def _slide_moves(
    board: Board,
    sq: int,
    piece: str,
    deltas: tuple[tuple[int, int], ...],
) -> list[Move]:
    moves: list[Move] = []
    for df, dr in deltas:
        f, r = file_of(sq) + df, rank_of(sq) + dr
        while 0 <= f <= 7 and 0 <= r <= 7:
            to = square_at(f, r)
            target = board.squares[to]
            if target is None:
                moves.append(Move(sq, to))
            else:
                if not same_color(piece, target):
                    moves.append(Move(sq, to))
                break
            f += df
            r += dr
    return moves


def _king_moves(board: Board, sq: int, piece: str) -> list[Move]:
    moves: list[Move] = []
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if df == 0 and dr == 0:
                continue
            f, r = file_of(sq) + df, rank_of(sq) + dr
            if not (0 <= f <= 7 and 0 <= r <= 7):
                continue
            to = square_at(f, r)
            target = board.squares[to]
            if target is None or not same_color(piece, target):
                moves.append(Move(sq, to))
    # Castling
    white = is_white(piece)
    if board.in_check(white):
        return moves
    enemy = not white
    if white:
        if "K" in board.castling and board.squares[5] is None and board.squares[6] is None:
            if not board.is_square_attacked(5, enemy) and not board.is_square_attacked(6, enemy):
                if board.squares[7] == "R":
                    moves.append(Move(4, 6, is_castle=True))
        if "Q" in board.castling and board.squares[1] is None and board.squares[2] is None and board.squares[3] is None:
            if not board.is_square_attacked(2, enemy) and not board.is_square_attacked(3, enemy):
                if board.squares[0] == "R":
                    moves.append(Move(4, 2, is_castle=True))
    else:
        if "k" in board.castling and board.squares[61] is None and board.squares[62] is None:
            if not board.is_square_attacked(61, enemy) and not board.is_square_attacked(62, enemy):
                if board.squares[63] == "r":
                    moves.append(Move(60, 62, is_castle=True))
        if "q" in board.castling and board.squares[57] is None and board.squares[58] is None and board.squares[59] is None:
            if not board.is_square_attacked(58, enemy) and not board.is_square_attacked(59, enemy):
                if board.squares[56] == "r":
                    moves.append(Move(60, 58, is_castle=True))
    return moves
