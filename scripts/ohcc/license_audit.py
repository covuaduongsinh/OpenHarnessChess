"""Lightweight license hygiene scan for OHCC (stub heuristics)."""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_TOKENS = (
    "stockfish",
    "python-chess",
    "from chess ",
    "from chess.",
    "import chess",
    "import chess.",
    "maia-chess",
    "maiachess",
)

# Files that only list banned names for policy messaging.
SKIP_PATH_PARTS = (
    "license_audit.py",
    "license-compliance.md",
    "THIRD_PARTY.md",
    "NOTICE.md",
    "README.md",
    "README.ohcc.md",
    "pedagogy.md",
)

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("ohcc", "plugins/ohcc-coach", "mcp-servers")


def _is_policy_doc(path: Path) -> bool:
    name = path.name
    return name in SKIP_PATH_PARTS or "license" in name.lower()


def main() -> int:
    hits: list[str] = []
    for rel in SCAN_DIRS:
        base = ROOT / rel
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or _is_policy_doc(path):
                continue
            if path.suffix.lower() not in {".py", ".toml", ".json", ".ts", ".tsx"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in FORBIDDEN_TOKENS:
                if token not in text:
                    continue
                window = text[max(0, text.find(token) - 80) : text.find(token) + 80]
                if any(
                    w in window
                    for w in (
                        "forbid",
                        "cấm",
                        "never",
                        "gpl",
                        "do not",
                        "don't",
                        "without",
                        "không",
                        "banned",
                        "no python-chess",
                        "not depend",
                    )
                ):
                    continue
                hits.append(f"{path.relative_to(ROOT)}: contains {token!r}")
    if hits:
        print("Potential license policy hits:")
        for h in hits:
            print(" -", h)
        return 1
    print("No forbidden engine/library tokens found in OHCC paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
