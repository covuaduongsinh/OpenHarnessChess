"""CLI: python -m ohcc.scaffolding --pgn path --vault path."""

from __future__ import annotations

import argparse
from pathlib import Path

from ohcc.scaffolding.puzzle_builder import ScaffoldingPuzzleBuilder


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Bloom scaffolding puzzles from PGN into an Obsidian vault."
    )
    parser.add_argument("--pgn", type=Path, required=True, help="Input PGN file")
    parser.add_argument(
        "--vault",
        type=Path,
        default=Path("vault"),
        help="Obsidian vault root (default: ./vault)",
    )
    parser.add_argument(
        "--level",
        choices=("preschool", "primary"),
        default="primary",
        help="Student level for Socratic wording",
    )
    parser.add_argument(
        "--max-moments",
        type=int,
        default=4,
        help="Max teaching moments per game",
    )
    parser.add_argument(
        "--arasan",
        action="store_true",
        help="Use Arasan (MIT) eval drops when ARASAN_PATH / vendor binary is available",
    )
    parser.add_argument(
        "--arasan-path",
        type=Path,
        default=None,
        help="Path to Arasan UCI binary (overrides ARASAN_PATH)",
    )
    parser.add_argument(
        "--eval-depth",
        type=int,
        default=10,
        help="Arasan depth when --arasan is set",
    )
    args = parser.parse_args(argv)

    builder = ScaffoldingPuzzleBuilder(
        vault_root=args.vault,
        student_level=args.level,
        max_moments_per_game=args.max_moments,
        arasan_mcp_enabled=args.arasan,
        arasan_path=args.arasan_path,
        eval_depth=args.eval_depth,
    )
    result = builder.build(pgn_path=args.pgn)
    print(f"Games: {result.games}")
    print(f"Moments: {len(result.moments)}")
    print(f"Puzzles written: {len(result.written)}")
    print(f"Arasan eval: {'yes' if result.used_arasan else 'no'}")
    for path in result.written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
