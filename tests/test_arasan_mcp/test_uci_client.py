"""UciClient integration against fake_uci_engine.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest import mock

from arasan_mcp.uci_client import UciClient

FAKE = Path(__file__).resolve().parents[1] / "fixtures" / "fake_uci_engine.py"
_real_popen = subprocess.Popen


def test_uci_client_handshake_and_analyze() -> None:
    def fake_popen(cmd, **kwargs):
        return _real_popen(
            [sys.executable, str(FAKE)],
            stdin=kwargs.get("stdin"),
            stdout=kwargs.get("stdout"),
            stderr=kwargs.get("stderr"),
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

    client = UciClient(engine_path=FAKE)
    with mock.patch("arasan_mcp.uci_client.subprocess.Popen", side_effect=fake_popen):
        client.start()
        try:
            result = client.analyze_fen(
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                depth=10,
            )
            assert result.bestmove == "e2e4"
            assert result.score_cp == 20
            assert result.depth >= 8
        finally:
            client.stop()
