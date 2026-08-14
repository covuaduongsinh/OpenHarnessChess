"""Run multi-provider LLM coach analysis and write vault reviews for admin UI.

Example:
  python scripts/ohcc/run_llm_coach_demo.py
  python scripts/ohcc/run_llm_coach_demo.py --providers claude,grok,antigravity
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from ohcc.llm_coach import analyze_game_with_llms, probe_providers  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--game",
        type=Path,
        default=ROOT / "vault" / "04-games" / "fools_mate.pgn",
    )
    parser.add_argument(
        "--fen",
        default="rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2",
        help="FEN before the teaching moment (default: before Qh4#)",
    )
    parser.add_argument("--san", default="Qh4#")
    parser.add_argument(
        "--providers",
        default="antigravity,claude,grok,codex",
        help="Comma-separated provider ids",
    )
    parser.add_argument("--timeout", type=int, default=150)
    args = parser.parse_args()

    print("=== Provider probe ===")
    for p in probe_providers():
        flag = "READY" if p.ready else "DOWN "
        print(f"  [{flag}] {p.id:12} {p.label}")
        print(f"           binary={p.binary}")
        print(f"           {p.detail[:120]}")

    providers = [x.strip() for x in args.providers.split(",") if x.strip()]
    out_dir = ROOT / "vault" / "_meta" / "llm-reviews"
    print(f"\n=== LLM coach analysis on {args.game.name} ===")
    print(f"Providers: {providers}")

    reviews = analyze_game_with_llms(
        game_path=args.game,
        fen=args.fen,
        san_moment=args.san,
        providers=providers,
        cwd=ROOT,
        timeout=args.timeout,
        out_dir=out_dir,
    )

    for r in reviews:
        print(f"\n--- {r.label} [{r.status}] {r.duration_ms}ms ---")
        if r.error:
            print(f"ERROR: {r.error[:300]}")
        if r.response:
            print(r.response[:1200])
            if len(r.response) > 1200:
                print("...")

    # status snapshot for admin
    status_path = out_dir / "providers-status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "id": p.id,
                        "label": p.label,
                        "ready": p.ready,
                        "binary": p.binary,
                        "detail": p.detail,
                    }
                    for p in probe_providers()
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote reviews under {out_dir}")
    print("Open admin: http://localhost:3100/llm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
