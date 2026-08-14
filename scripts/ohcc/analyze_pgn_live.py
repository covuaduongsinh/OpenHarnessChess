"""End-to-end live analysis: PGN → chess pipeline → one LLM coach.

Stdout: single JSON object (for Next.js API).
Usage:
  python scripts/ohcc/analyze_pgn_live.py --provider claude --pgn-file path.pgn
  python scripts/ohcc/analyze_pgn_live.py --provider grok --pgn-text "..."
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from ohcc.chess_core.heuristics.hanging import find_hanging_pieces  # noqa: E402
from ohcc.chess_core.pgn import read_pgn_file, read_pgn_text, replay_game  # noqa: E402
from ohcc.llm_coach import (  # noqa: E402
    build_coach_prompt,
    probe_providers,
    run_provider_analysis,
)
from ohcc.scaffolding.bloom import BloomLevel  # noqa: E402
from ohcc.scaffolding.mistake_detect import detect_teaching_moments  # noqa: E402
from ohcc.scaffolding.questions import questions_for_moment  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def analyze_live(
    *,
    pgn_text: str,
    provider: str,
    timeout: int = 180,
    student_level: str = "primary",
    max_moments: int = 4,
) -> dict:
    t0 = time.perf_counter()
    steps: list[dict] = []

    def step(name: str, status: str, detail: str, **extra) -> None:
        steps.append(
            {
                "t_ms": int((time.perf_counter() - t0) * 1000),
                "name": name,
                "status": status,
                "detail": detail,
                **extra,
            }
        )

    # --- 0 probe ---
    probes = {p.id: p for p in probe_providers()}
    prov = probes.get(provider)
    if prov is None:
        return {
            "ok": False,
            "error": f"Unknown provider: {provider}",
            "steps": steps,
            "created": _now(),
        }
    step(
        "probe_cli",
        "ok" if prov.ready else "error",
        f"{prov.label}: {'ready' if prov.ready else prov.detail}",
        binary=prov.binary,
        provider=provider,
    )
    if not prov.ready:
        return {
            "ok": False,
            "error": f"Provider {provider} not ready: {prov.detail}",
            "steps": steps,
            "provider_status": {
                "id": prov.id,
                "ready": prov.ready,
                "binary": prov.binary,
                "detail": prov.detail,
            },
            "created": _now(),
        }

    # --- 1 parse ---
    games = read_pgn_text(pgn_text)
    if not games or not games[0].moves:
        step("parse_pgn", "error", "Không parse được nước đi từ PGN")
        return {
            "ok": False,
            "error": "Invalid or empty PGN (no moves)",
            "steps": steps,
            "created": _now(),
        }
    game = games[0]
    step(
        "parse_pgn",
        "ok",
        f"White={game.white} Black={game.black} moves={len(game.moves)}",
        headers=game.headers,
        moves=game.moves,
    )

    # --- 2 replay ---
    try:
        plies = replay_game(game)
    except Exception as exc:
        step("replay", "error", str(exc))
        return {"ok": False, "error": f"Replay failed: {exc}", "steps": steps, "created": _now()}

    ply_rows = []
    for ply in plies:
        hanging = find_hanging_pieces(ply.fen_after, for_side_white=ply.side_moved_white)
        signals = []
        if ply.is_capture:
            signals.append("capture")
        if ply.is_check:
            signals.append("check")
        if ply.is_mate:
            signals.append("mate")
        if hanging:
            signals.append(f"hanging:{','.join(hanging)}")
        ply_rows.append(
            {
                "ply": ply.ply_index,
                "san": ply.san,
                "side": "white" if ply.side_moved_white else "black",
                "fen_before": ply.fen_before,
                "fen_after": ply.fen_after,
                "signals": signals,
            }
        )
    step("replay", "ok", f"Replay {len(plies)} half-moves (SAN→FEN)", ply_count=len(plies))

    # --- 3 detect moments ---
    moments = detect_teaching_moments(plies, max_moments=max_moments)
    moment_rows = []
    for m in moments:
        qs = questions_for_moment(m, student_level=student_level)
        moment_rows.append(
            {
                "kind": m.kind,
                "severity": m.severity,
                "ply": m.ply.ply_index,
                "san": m.ply.san,
                "fen": m.fen,
                "note": m.note,
                "drop_cp": m.drop_cp,
                "bloom": {
                    "remember": qs[BloomLevel.REMEMBER],
                    "apply": qs[BloomLevel.APPLY],
                    "analyze": qs[BloomLevel.ANALYZE],
                },
            }
        )
    step(
        "detect_moments",
        "ok",
        f"Heuristic chọn {len(moments)} teaching moment(s)",
        kinds=[m.kind for m in moments],
    )

    # Pick primary moment for LLM (first, prefer mate/check/hanging)
    primary = moments[0] if moments else None
    if not primary and plies:
        # fallback: last position before final move
        last = plies[-1]
        fen = last.fen_before
        san = last.san
    elif primary:
        fen = primary.fen
        san = primary.ply.san
    else:
        fen = game.starting_fen
        san = "(start)"

    step(
        "select_moment",
        "ok",
        f"Moment gửi LLM: SAN={san} kind={primary.kind if primary else 'fallback'}",
        fen=fen,
        san=san,
    )

    # --- 4 build prompt ---
    title = game.headers.get("Event") or f"{game.white} vs {game.black}"
    prompt = build_coach_prompt(
        game_title=title,
        pgn=pgn_text,
        fen=fen,
        san_moment=san,
    )
    step("build_prompt", "ok", f"Prompt Thầy Tường ({len(prompt)} chars)", prompt_excerpt=prompt[:280])

    # --- 5 LLM ---
    step("llm_start", "running", f"Gọi CLI provider={provider} timeout={timeout}s")
    review = run_provider_analysis(provider, prompt, cwd=ROOT, timeout=timeout)
    step(
        "llm_finish",
        review.status,
        f"{review.label}: {review.status} in {review.duration_ms}ms",
        duration_ms=review.duration_ms,
        error=review.error or None,
    )

    # optional save under vault
    out_dir = ROOT / "vault" / "_meta" / "llm-reviews" / "live"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = {
        "ok": review.status == "ok",
        "created": _now(),
        "provider": provider,
        "provider_label": review.label,
        "binary": review.binary,
        "game": {
            "white": game.white,
            "black": game.black,
            "event": title,
            "headers": game.headers,
            "moves": game.moves,
            "move_count": len(game.moves),
        },
        "steps": steps,
        "plies": ply_rows,
        "moments": moment_rows,
        "selected_moment": {
            "fen": fen,
            "san": san,
            "kind": primary.kind if primary else "fallback",
        },
        "prompt": prompt,
        "llm": review.as_dict(),
        "total_ms": int((time.perf_counter() - t0) * 1000),
    }
    save_path = out_dir / f"live-{provider}-{stamp}.json"
    save_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["saved"] = str(save_path.relative_to(ROOT)).replace("\\", "/")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, choices=["antigravity", "claude", "grok", "codex"])
    parser.add_argument("--pgn-file", type=Path, default=None)
    parser.add_argument("--pgn-text", type=str, default=None)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-moments", type=int, default=4)
    args = parser.parse_args()

    if args.pgn_file:
        pgn_text = args.pgn_file.read_text(encoding="utf-8")
    elif args.pgn_text:
        pgn_text = args.pgn_text
    else:
        # read full stdin
        pgn_text = sys.stdin.read()

    if not pgn_text.strip():
        print(json.dumps({"ok": False, "error": "Empty PGN"}, ensure_ascii=False))
        return 1

    result = analyze_live(
        pgn_text=pgn_text,
        provider=args.provider,
        timeout=args.timeout,
        max_moments=args.max_moments,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
