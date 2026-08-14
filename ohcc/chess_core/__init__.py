"""MIT-safe chess primitives.

Do NOT depend on python-chess (GPL-3), Stockfish (GPL), or Maia (GPL).
Engine analysis is delegated to Arasan (MIT) through arasan-mcp.
"""

from ohcc.chess_core.board import Board
from ohcc.chess_core.fen import START_FEN
from ohcc.chess_core.pgn import PgnGame, read_pgn_file, read_pgn_text, replay_game

__all__ = [
    "Board",
    "START_FEN",
    "PgnGame",
    "read_pgn_file",
    "read_pgn_text",
    "replay_game",
]
