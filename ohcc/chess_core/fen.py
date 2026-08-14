"""FEN encode/decode helpers (MIT)."""

from __future__ import annotations

from ohcc.chess_core.squares import square_name

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

PIECE_CHARS = set("pnbrqkPNBRQK")


def split_fen(fen: str) -> list[str]:
    """Split a FEN string into fields (pad to 6 when short)."""
    parts = fen.strip().split()
    if len(parts) < 4:
        raise ValueError(f"Invalid FEN (need at least 4 fields): {fen!r}")
    while len(parts) < 6:
        parts.append("0" if len(parts) == 4 else "1")
    return parts[:6]


def side_to_move(fen: str) -> str:
    """Return 'w' or 'b' from a FEN string."""
    return split_fen(fen)[1]


def parse_placement(placement: str) -> list[str | None]:
    """Parse FEN piece placement into a 64-slot board (a1..h8)."""
    board: list[str | None] = [None] * 64
    rank = 7
    file = 0
    for ch in placement:
        if ch == "/":
            rank -= 1
            file = 0
            if rank < 0:
                raise ValueError(f"Too many ranks in FEN: {placement!r}")
            continue
        if ch.isdigit():
            file += int(ch)
            if file > 8:
                raise ValueError(f"Rank overflow in FEN: {placement!r}")
            continue
        if ch not in PIECE_CHARS:
            raise ValueError(f"Invalid piece in FEN: {ch!r}")
        if file > 7 or rank < 0:
            raise ValueError(f"Placement overflow in FEN: {placement!r}")
        sq = file + 8 * rank
        board[sq] = ch
        file += 1
    return board


def encode_placement(board: list[str | None]) -> str:
    """Encode a 64-slot board into FEN placement."""
    ranks: list[str] = []
    for rank in range(7, -1, -1):
        empty = 0
        row = []
        for file in range(8):
            piece = board[file + 8 * rank]
            if piece is None:
                empty += 1
            else:
                if empty:
                    row.append(str(empty))
                    empty = 0
                row.append(piece)
        if empty:
            row.append(str(empty))
        ranks.append("".join(row))
    return "/".join(ranks)


def ep_to_square(ep: str) -> int | None:
    if not ep or ep == "-":
        return None
    from ohcc.chess_core.squares import square_from_name

    return square_from_name(ep)


def square_to_ep(sq: int | None) -> str:
    if sq is None:
        return "-"
    return square_name(sq)
