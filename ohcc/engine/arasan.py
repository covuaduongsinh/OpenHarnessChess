"""Arasan evaluator adapter used by scaffolding (optional runtime).

Imports ``arasan_mcp`` when available on PYTHONPATH (mcp-servers/arasan-mcp/src).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class EvalSnapshot:
    """Side-to-move score snapshot."""

    fen: str
    score_cp: int | None
    mate: int | None
    depth: int
    bestmove: str | None = None


class PositionEvaluator(Protocol):
    """Protocol for evaluate(fen) → snapshot."""

    def evaluate(self, fen: str, *, depth: int = 10) -> EvalSnapshot: ...

    def close(self) -> None: ...


def _ensure_arasan_mcp_path() -> None:
    root = Path(__file__).resolve().parents[2]
    src = root / "mcp-servers" / "arasan-mcp" / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


class ArasanEvaluator:
    """Thin wrapper around arasan_mcp.UciClient for scaffolding."""

    def __init__(
        self,
        engine_path: str | Path | None = None,
        *,
        default_depth: int = 10,
    ) -> None:
        _ensure_arasan_mcp_path()
        from arasan_mcp.uci_client import UciClient

        self._client = UciClient.from_env(engine_path)
        self._client.start()
        self.default_depth = default_depth

    def evaluate(self, fen: str, *, depth: int | None = None) -> EvalSnapshot:
        result = self._client.evaluate_position(fen, depth=depth or self.default_depth)
        return EvalSnapshot(
            fen=fen,
            score_cp=result.score_cp,
            mate=result.mate,
            depth=result.depth,
            bestmove=result.bestmove,
        )

    def close(self) -> None:
        self._client.stop()

    def __enter__(self) -> ArasanEvaluator:
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class CallableEvaluator:
    """Adapter: wrap a pure function as PositionEvaluator (for tests)."""

    def __init__(self, fn) -> None:
        self._fn = fn

    def evaluate(self, fen: str, *, depth: int = 10) -> EvalSnapshot:
        _ = depth
        return self._fn(fen)

    def close(self) -> None:
        return None
