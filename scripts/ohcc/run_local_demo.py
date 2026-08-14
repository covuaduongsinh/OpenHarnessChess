"""Run a full local OHCC demo: scaffolding + vision inbox + summary.

Usage (from repo root):
  python scripts/ohcc/run_local_demo.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp-servers" / "vision-board-mcp" / "src"))

from ohcc.scaffolding import ScaffoldingPuzzleBuilder  # noqa: E402
from vision_board_mcp.board_vision import analyze_board_image  # noqa: E402


def copy_sample_pgns(vault_games: Path) -> list[Path]:
    src = ROOT / "data" / "sample-pgn"
    vault_games.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for pgn in sorted(src.glob("*.pgn")):
        dest = vault_games / pgn.name
        shutil.copy2(pgn, dest)
        copied.append(dest)
    return copied


def make_demo_png(path: Path) -> Path:
    """Write a tiny valid PNG for vision intake demo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return path


def main() -> int:
    vault = ROOT / "vault"
    games_dir = vault / "04-games"
    inbox = vault / "00-inbox"
    fixtures = ROOT / "data" / "fixtures" / "boards"

    print("=== OHCC local demo ===")
    print(f"Repo: {ROOT}")
    print(f"Vault: {vault}")

    # 1) Copy PGNs into vault
    copied = copy_sample_pgns(games_dir)
    print(f"\n[1] Copied {len(copied)} PGN(s) -> vault/04-games/")
    for p in copied:
        print(f"    - {p.name}")

    # 2) Scaffolding for each sample PGN
    builder = ScaffoldingPuzzleBuilder(
        vault_root=vault,
        student_level="primary",
        max_moments_per_game=3,
    )
    total_puzzles = 0
    total_moments = 0
    print("\n[2] ScaffoldingPuzzleBuilder (heuristic moments)")
    for pgn in sorted((ROOT / "data" / "sample-pgn").glob("*.pgn")):
        result = builder.build(pgn_path=pgn, source_label=f"demo/{pgn.name}")
        total_puzzles += len(result.written)
        total_moments += len(result.moments)
        print(
            f"    {pgn.name}: games={result.games} moments={len(result.moments)} "
            f"puzzles={len(result.written)}"
        )
    print(f"    TOTAL moments={total_moments} puzzles={total_puzzles}")

    # 3) Vision intake with fen_hint (teacher confirmed start position)
    img = make_demo_png(fixtures / "demo_board.png")
    start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    vision = analyze_board_image(img, fen_hint=start_fen, vault_inbox=inbox)
    print("\n[3] vision-board intake")
    print(f"    image: {img}")
    print(f"    ok={vision.ok} source={vision.source} fen={vision.fen}")
    print(f"    inbox_note: {vision.inbox_note}")

    # 4) Pending photo without hint
    img2 = make_demo_png(fixtures / "demo_board_pending.jpg")
    # .jpg suffix for path check
    pending_path = fixtures / "demo_board_pending.jpg"
    pending_path.write_bytes(img2.read_bytes())
    vision2 = analyze_board_image(pending_path, vault_inbox=inbox)
    print("\n[4] vision pending (no fen_hint)")
    print(f"    ok={vision2.ok} source={vision2.source}")
    print(f"    inbox_note: {vision2.inbox_note}")

    # 5) Summary counts
    def count_md(rel: str) -> int:
        d = vault / rel
        if not d.exists():
            return 0
        return sum(1 for _ in d.rglob("*.md"))

    print("\n[5] Vault summary")
    print(f"    students:  {count_md('01-students')}")
    print(f"    lessons:   {count_md('02-lessons')}")
    print(f"    puzzles:   {count_md('03-puzzles')}")
    print(f"    games pgn: {len(list((vault / '04-games').glob('*.pgn')))}")
    print(f"    inbox:     {count_md('00-inbox')}")

    # 6) Export analysis process traces for admin /analysis UI
    print("\n[6] Export analysis traces (model process log)")
    import subprocess

    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ohcc" / "export_analysis_traces.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    print((r.stdout or "") + (r.stderr or ""))

    print("\n=== Next: admin portal ===")
    print("  cd admin-portal")
    print("  $env:OHCC_VAULT = (Resolve-Path ..\\vault).Path")
    print("  npm run dev")
    print("  open http://localhost:3100/analysis")
    print("\nDemo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
