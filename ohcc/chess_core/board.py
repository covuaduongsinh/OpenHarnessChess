"""Mutable chess board with FEN I/O and legal move helpers (MIT)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ohcc.chess_core.fen import (
    START_FEN,
    encode_placement,
    ep_to_square,
    parse_placement,
    split_fen,
    square_to_ep,
)
from ohcc.chess_core.squares import file_of, rank_of, square_at, square_name


def is_white(piece: str) -> bool:
    return piece.isupper()


def is_black(piece: str) -> bool:
    return piece.islower()


def same_color(a: str, b: str) -> bool:
    return is_white(a) == is_white(b)


@dataclass
class Board:
    """Position with castling rights, ep, clocks, and side to move."""

    squares: list[str | None] = field(default_factory=lambda: [None] * 64)
    turn_white: bool = True
    castling: str = "KQkq"
    ep_square: int | None = None
    halfmove: int = 0
    fullmove: int = 1

    @classmethod
    def starting(cls) -> Board:
        return cls.from_fen(START_FEN)

    @classmethod
    def from_fen(cls, fen: str) -> Board:
        placement, stm, castling, ep, half, full = split_fen(fen)
        return cls(
            squares=parse_placement(placement),
            turn_white=(stm == "w"),
            castling=castling if castling != "-" else "",
            ep_square=ep_to_square(ep),
            halfmove=int(half),
            fullmove=int(full),
        )

    def fen(self) -> str:
        castling = self.castling if self.castling else "-"
        return " ".join(
            [
                encode_placement(self.squares),
                "w" if self.turn_white else "b",
                castling,
                square_to_ep(self.ep_square),
                str(self.halfmove),
                str(self.fullmove),
            ]
        )

    def copy(self) -> Board:
        return Board(
            squares=list(self.squares),
            turn_white=self.turn_white,
            castling=self.castling,
            ep_square=self.ep_square,
            halfmove=self.halfmove,
            fullmove=self.fullmove,
        )

    def piece_at(self, sq: int) -> str | None:
        return self.squares[sq]

    def king_square(self, white: bool) -> int | None:
        target = "K" if white else "k"
        for sq, piece in enumerate(self.squares):
            if piece == target:
                return sq
        return None

    def is_square_attacked(self, sq: int, by_white: bool) -> bool:
        """Return True if *sq* is attacked by the given side."""
        # Pawn attacks
        direction = 1 if by_white else -1
        rank = rank_of(sq)
        file = file_of(sq)
        for df in (-1, 1):
            f, r = file + df, rank - direction
            if 0 <= f <= 7 and 0 <= r <= 7:
                piece = self.squares[square_at(f, r)]
                if piece == ("P" if by_white else "p"):
                    return True

        # Knight
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
            f, r = file + df, rank + dr
            if 0 <= f <= 7 and 0 <= r <= 7:
                piece = self.squares[square_at(f, r)]
                if piece == ("N" if by_white else "n"):
                    return True

        # King
        for df in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if df == 0 and dr == 0:
                    continue
                f, r = file + df, rank + dr
                if 0 <= f <= 7 and 0 <= r <= 7:
                    piece = self.squares[square_at(f, r)]
                    if piece == ("K" if by_white else "k"):
                        return True

        # Sliding: bishop/queen diagonals, rook/queen orthogonals
        for df, dr, sliders in (
            (1, 0, "RQ"),
            (-1, 0, "RQ"),
            (0, 1, "RQ"),
            (0, -1, "RQ"),
            (1, 1, "BQ"),
            (1, -1, "BQ"),
            (-1, 1, "BQ"),
            (-1, -1, "BQ"),
        ):
            f, r = file + df, rank + dr
            while 0 <= f <= 7 and 0 <= r <= 7:
                piece = self.squares[square_at(f, r)]
                if piece is not None:
                    want = sliders if by_white else sliders.lower()
                    if piece in want:
                        return True
                    break
                f += df
                r += dr
        return False

    def in_check(self, white: bool | None = None) -> bool:
        side = self.turn_white if white is None else white
        king = self.king_square(side)
        if king is None:
            return False
        return self.is_square_attacked(king, by_white=not side)

    def clear_castling_for_square(self, sq: int) -> None:
        mapping = {
            0: "Q",  # a1
            4: "KQ",  # e1
            7: "K",  # h1
            56: "q",  # a8
            60: "kq",  # e8
            63: "k",  # h8
        }
        remove = mapping.get(sq, "")
        self.castling = "".join(c for c in self.castling if c not in remove)
