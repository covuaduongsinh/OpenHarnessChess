"""UCI subprocess client for Arasan (MIT) or compatible UCI engines."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from arasan_mcp.analysis import AnalysisResult, parse_bestmove_line, parse_info_line


class UciError(RuntimeError):
    """Raised when the UCI engine fails or times out."""


def resolve_engine_path(explicit: str | Path | None = None) -> Path:
    """Resolve Arasan binary from argument, ARASAN_PATH, or vendor defaults."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("ARASAN_PATH")
    if env:
        candidates.append(Path(env))
    # Repo-relative defaults (when running from monorepo root)
    root = Path.cwd()
    candidates.extend(
        [
            root / "vendor" / "arasan" / "bin" / "arasan.exe",
            root / "vendor" / "arasan" / "bin" / "arasan",
        ]
    )
    for path in candidates:
        if path.is_file():
            return path.resolve()
    tried = ", ".join(str(p) for p in candidates) or "(none)"
    raise UciError(
        "Arasan binary not found. Set ARASAN_PATH or place a MIT Arasan build at "
        f"vendor/arasan/bin/. Tried: {tried}"
    )


@dataclass
class UciClient:
    """Thin wrapper around an Arasan (or compatible MIT UCI) binary."""

    engine_path: Path
    startup_timeout: float = 10.0
    analyze_timeout: float = 60.0
    _proc: subprocess.Popen[str] | None = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _name: str = field(default="arasan", init=False)

    @classmethod
    def from_env(cls, explicit: str | Path | None = None, **kwargs) -> UciClient:
        return cls(engine_path=resolve_engine_path(explicit), **kwargs)

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        """Start the engine process and complete UCI handshake."""
        with self._lock:
            if self.is_running:
                return
            path = Path(self.engine_path)
            if not path.is_file():
                raise UciError(f"Engine not found: {path}")
            self._proc = subprocess.Popen(
                [str(path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
            self._write("uci")
            deadline = time.monotonic() + self.startup_timeout
            while time.monotonic() < deadline:
                line = self._readline(timeout=deadline - time.monotonic())
                if line is None:
                    break
                if line.startswith("id name"):
                    self._name = line[len("id name") :].strip() or self._name
                if line == "uciok":
                    self._write("isready")
                    self._wait_for("readyok", timeout=self.startup_timeout)
                    return
            self.stop()
            raise UciError(f"UCI handshake failed for {path}")

    def stop(self) -> None:
        """Quit the engine process."""
        with self._lock:
            proc = self._proc
            self._proc = None
            if proc is None:
                return
            try:
                if proc.poll() is None and proc.stdin:
                    proc.stdin.write("quit\n")
                    proc.stdin.flush()
                    proc.wait(timeout=2)
            except Exception:
                pass
            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass

    def __enter__(self) -> UciClient:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def new_game(self) -> None:
        self._ensure_running()
        self._write("ucinewgame")
        self._write("isready")
        self._wait_for("readyok", timeout=self.startup_timeout)

    def analyze_fen(
        self,
        fen: str,
        *,
        depth: int = 12,
        movetime_ms: int | None = None,
        multipv: int = 1,
    ) -> AnalysisResult:
        """Analyze a FEN; returns bestmove, score, and PV (coach-internal)."""
        self._ensure_running()
        with self._lock:
            if multipv > 1:
                self._write(f"setoption name MultiPV value {multipv}")
            self._write(f"position fen {fen}")
            if movetime_ms is not None:
                self._write(f"go movetime {int(movetime_ms)}")
            else:
                self._write(f"go depth {int(depth)}")

            result = AnalysisResult(fen=fen)
            deadline = time.monotonic() + self.analyze_timeout
            while time.monotonic() < deadline:
                line = self._readline(timeout=deadline - time.monotonic())
                if line is None:
                    break
                if line.startswith("info "):
                    parse_info_line(line, result)
                elif line.startswith("bestmove"):
                    result.bestmove = parse_bestmove_line(line)
                    if multipv > 1:
                        self._write("setoption name MultiPV value 1")
                    return result
            if multipv > 1:
                self._write("setoption name MultiPV value 1")
            raise UciError(f"Analyze timed out for FEN: {fen}")

    def evaluate_position(self, fen: str, *, depth: int = 8) -> AnalysisResult:
        """Quick evaluation of a FEN (shallower depth)."""
        return self.analyze_fen(fen, depth=depth)

    def _ensure_running(self) -> None:
        if not self.is_running:
            self.start()

    def _write(self, command: str) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            raise UciError("Engine is not running")
        proc.stdin.write(command + "\n")
        proc.stdin.flush()

    def _readline(self, timeout: float) -> str | None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return None
        if timeout <= 0:
            return None
        line_holder: list[str | None] = [None]

        def _reader() -> None:
            try:
                line_holder[0] = proc.stdout.readline()  # type: ignore[union-attr]
            except Exception:
                line_holder[0] = None

        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            return None
        raw = line_holder[0]
        if raw is None:
            return None
        return raw.strip()

    def _wait_for(self, token: str, *, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._readline(timeout=deadline - time.monotonic())
            if line is None:
                break
            if line == token or line.startswith(token + " "):
                return
        raise UciError(f"Timeout waiting for {token!r}")
