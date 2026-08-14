"""PGN reader (MIT) — headers, SAN moves, multi-game files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ohcc.chess_core.board import Board
from ohcc.chess_core.fen import START_FEN
from ohcc.chess_core.san import apply_san, normalize_san

_HEADER_RE = re.compile(r'^\[(\w+)\s+"(.*)"\]\s*$')
_MOVE_NUM_RE = re.compile(r"^\d+\.(\.\.)?$")
_RESULT_TOKENS = {"1-0", "0-1", "1/2-1/2", "*"}


@dataclass
class PgnGame:
    """Lightweight PGN game container."""

    headers: dict[str, str] = field(default_factory=dict)
    moves: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def white(self) -> str:
        return self.headers.get("White", "White")

    @property
    def black(self) -> str:
        return self.headers.get("Black", "Black")

    @property
    def starting_fen(self) -> str:
        return self.headers.get("FEN", START_FEN)


@dataclass
class ReplayPly:
    """One half-move in a replayed game."""

    ply_index: int  # 1-based ply number
    san: str
    fen_before: str
    fen_after: str
    is_capture: bool
    is_check: bool
    is_mate: bool
    side_moved_white: bool


def read_pgn_text(text: str) -> list[PgnGame]:
    """Parse PGN text into one or more games."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    games: list[PgnGame] = []
    chunks = _split_games(text)
    for chunk in chunks:
        game = _parse_game_chunk(chunk)
        if game.headers or game.moves:
            games.append(game)
    return games


def read_pgn_file(path: Path) -> list[PgnGame]:
    """Read a PGN file from disk."""
    return read_pgn_text(path.read_text(encoding="utf-8"))


def replay_game(game: PgnGame) -> list[ReplayPly]:
    """Replay SAN moves and return per-ply position snapshots."""
    board = Board.from_fen(game.starting_fen)
    plies: list[ReplayPly] = []
    for i, san in enumerate(game.moves, start=1):
        fen_before = board.fen()
        side_white = board.turn_white
        cleaned = normalize_san(san)
        is_check = cleaned.endswith("+") or cleaned.endswith("#")
        is_mate = cleaned.endswith("#")
        is_capture = "x" in cleaned
        board = apply_san(board, cleaned)
        # Prefer board-derived check after move for robustness
        after_check = board.in_check()
        plies.append(
            ReplayPly(
                ply_index=i,
                san=cleaned,
                fen_before=fen_before,
                fen_after=board.fen(),
                is_capture=is_capture,
                is_check=is_check or after_check,
                is_mate=is_mate,
                side_moved_white=side_white,
            )
        )
    return plies


def _split_games(text: str) -> list[str]:
    lines = text.split("\n")
    chunks: list[list[str]] = []
    current: list[str] = []
    seen_moves = False
    for line in lines:
        if line.startswith("[") and seen_moves and current:
            chunks.append(current)
            current = [line]
            seen_moves = False
            continue
        if line.startswith("["):
            current.append(line)
            continue
        if line.strip():
            seen_moves = True
        current.append(line)
    if current:
        chunks.append(current)
    return ["\n".join(c).strip() for c in chunks if any(x.strip() for x in c)]


def _parse_game_chunk(chunk: str) -> PgnGame:
    headers: dict[str, str] = {}
    body_lines: list[str] = []
    for line in chunk.split("\n"):
        hm = _HEADER_RE.match(line.strip())
        if hm:
            headers[hm.group(1)] = hm.group(2)
        else:
            body_lines.append(line)
    body = "\n".join(body_lines)
    body = _strip_comments(body)
    tokens = body.split()
    moves: list[str] = []
    for tok in tokens:
        if _MOVE_NUM_RE.match(tok):
            continue
        if tok in _RESULT_TOKENS:
            continue
        # Drop NAGs like $1 $2
        if tok.startswith("$"):
            continue
        moves.append(tok)
    return PgnGame(headers=headers, moves=moves, raw=chunk)


def _strip_comments(body: str) -> str:
    """Remove {comments}, ; line comments, and (RAVs)."""
    out: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if ch == "{":
            j = body.find("}", i + 1)
            i = n if j < 0 else j + 1
            continue
        if ch == ";":
            j = body.find("\n", i + 1)
            i = n if j < 0 else j
            continue
        if ch == "(":
            depth = 1
            i += 1
            while i < n and depth:
                if body[i] == "(":
                    depth += 1
                elif body[i] == ")":
                    depth -= 1
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)
