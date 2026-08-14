"""Square indexing helpers (a1=0 … h8=63)."""

from __future__ import annotations

FILES = "abcdefgh"
RANKS = "12345678"


def square_from_name(name: str) -> int:
    """Convert algebraic square name (e.g. 'e4') to 0..63."""
    name = name.strip().lower()
    if len(name) != 2 or name[0] not in FILES or name[1] not in RANKS:
        raise ValueError(f"Invalid square: {name!r}")
    return FILES.index(name[0]) + 8 * RANKS.index(name[1])


def square_name(sq: int) -> str:
    """Convert 0..63 to algebraic name."""
    if not 0 <= sq <= 63:
        raise ValueError(f"Square out of range: {sq}")
    return f"{FILES[sq % 8]}{RANKS[sq // 8]}"


def file_of(sq: int) -> int:
    return sq % 8


def rank_of(sq: int) -> int:
    return sq // 8


def in_bounds(file: int, rank: int) -> bool:
    return 0 <= file <= 7 and 0 <= rank <= 7


def square_at(file: int, rank: int) -> int:
    return file + 8 * rank
