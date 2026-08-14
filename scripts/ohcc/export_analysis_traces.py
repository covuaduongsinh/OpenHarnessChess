"""Export step-by-step analysis traces for admin UI.

Writes vault/_meta/analysis-traces/<game>.json describing each model stage.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ohcc.chess_core.heuristics.hanging import find_hanging_pieces
from ohcc.chess_core.pgn import read_pgn_file, replay_game
from ohcc.scaffolding.mistake_detect import detect_teaching_moments
from ohcc.scaffolding.questions import questions_for_moment
from ohcc.scaffolding.bloom import BloomLevel


def build_trace(pgn_path: Path) -> dict:
    games = read_pgn_file(pgn_path)
    if not games:
        return {"error": "no games", "gameFile": pgn_path.name}

    game = games[0]
    plies = replay_game(game)
    moments = detect_teaching_moments(plies, max_moments=8)

    ply_rows = []
    for ply in plies:
        hanging_mover = find_hanging_pieces(
            ply.fen_after, for_side_white=ply.side_moved_white
        )
        signals = []
        if ply.is_capture:
            signals.append({"code": "capture", "label": "Nuoc bat quan (SAN co x)"})
        if ply.is_check:
            signals.append({"code": "check", "label": "Chieu vua sau nuoc di"})
        if ply.is_mate:
            signals.append({"code": "mate", "label": "Chieu het"})
        if hanging_mover:
            signals.append(
                {
                    "code": "hanging",
                    "label": f"Quan treo sau nuoc: {', '.join(hanging_mover)}",
                    "squares": hanging_mover,
                }
            )
        ply_rows.append(
            {
                "ply": ply.ply_index,
                "san": ply.san,
                "side": "white" if ply.side_moved_white else "black",
                "fen_before": ply.fen_before,
                "fen_after": ply.fen_after,
                "signals": signals,
                "selected_as_teaching_moment": any(
                    m.ply.ply_index == ply.ply_index for m in moments
                ),
            }
        )

    moment_rows = []
    for m in moments:
        qs = questions_for_moment(m, student_level="primary")
        rules = []
        if m.kind == "mate":
            rules.append("Rule: is_mate == True tren ReplayPly")
        if m.kind == "check":
            rules.append("Rule: is_check == True (SAN +/# hoac board.in_check)")
        if m.kind == "capture":
            rules.append("Rule: is_capture == True va khong phai check")
        if m.kind == "hanging":
            rules.append("Rule: find_hanging_pieces(fen_after) khong rong")
        if m.kind == "eval_drop":
            rules.append("Rule: Arasan mover_drop_cp >= 50")
        moment_rows.append(
            {
                "kind": m.kind,
                "severity": m.severity,
                "ply": m.ply.ply_index,
                "san": m.ply.san,
                "fen": m.fen,
                "note": m.note,
                "drop_cp": m.drop_cp,
                "detection_rules": rules,
                "bloom_outputs": {
                    "remember": qs[BloomLevel.REMEMBER],
                    "apply": qs[BloomLevel.APPLY],
                    "analyze": qs[BloomLevel.ANALYZE],
                },
            }
        )

    stages = [
        {
            "id": 1,
            "model": "ohcc.chess_core.pgn",
            "title": "Doc & parse PGN",
            "status": "ok",
            "detail": (
                f"Headers: White={game.white}, Black={game.black}; "
                f"{len(game.moves)} nuoc SAN."
            ),
            "io": {"input": pgn_path.name, "output": f"{len(game.moves)} moves"},
        },
        {
            "id": 2,
            "model": "ohcc.chess_core.san + board + movegen",
            "title": "Replay van (SAN -> FEN)",
            "status": "ok",
            "detail": (
                f"Ap dung {len(plies)} half-move; moi ply co fen_before/fen_after. "
                "MIT, khong python-chess."
            ),
            "io": {"input": "SAN list", "output": f"{len(plies)} ReplayPly"},
        },
        {
            "id": 3,
            "model": "ohcc.scaffolding.mistake_detect + heuristics",
            "title": "Heuristic: bat tin hieu day",
            "status": "ok",
            "detail": (
                "Quet tung ply: capture / check / mate / hanging pieces. "
                f"Chon {len(moments)} teaching moment."
            ),
            "io": {
                "input": f"{len(plies)} plies",
                "output": [m.kind for m in moments],
            },
        },
        {
            "id": 4,
            "model": "arasan-mcp (UCI MIT)",
            "title": "Engine Arasan eval drop",
            "status": "skipped",
            "detail": (
                "Chua bat --arasan / ARASAN_PATH trong ban demo nay. "
                "Khi bat: compare fen_before vs fen_after -> drop_cp -> "
                "inaccuracy/mistake/blunder. Cam Stockfish/Maia."
            ),
            "io": {"input": "FEN pairs", "output": "drop_cp (optional)"},
        },
        {
            "id": 5,
            "model": "ohcc.scaffolding.questions (Bloom)",
            "title": "Sinh cau hoi Bloom x3",
            "status": "ok",
            "detail": (
                "Moi moment -> remember / apply / analyze (Socratic). "
                "Khong spoiler nuoc di giai."
            ),
            "io": {
                "input": f"{len(moments)} moments",
                "output": f"{len(moments) * 3} prompts",
            },
        },
        {
            "id": 6,
            "model": "Thay Tuong persona",
            "title": "Khung su pham (coach)",
            "status": "policy",
            "detail": (
                "System prompt: Socratic first, 1 cau hoi/luot, khong dump eval tho "
                "cho hoc vien mam non/tieu hoc."
            ),
            "io": {"input": "prompts + FEN", "output": "loi coach (runtime LLM)"},
        },
    ]

    return {
        "gameFile": pgn_path.name,
        "event": game.headers.get("Event", pgn_path.stem),
        "white": game.white,
        "black": game.black,
        "moveCount": len(game.moves),
        "moves": game.moves,
        "stages": stages,
        "plies": ply_rows,
        "moments": moment_rows,
        "models_summary": [
            {
                "name": "chess_core",
                "license": "MIT (in-repo)",
                "role": "PGN parse + SAN replay + board",
            },
            {
                "name": "heuristic detector",
                "license": "MIT (in-repo)",
                "role": "check/capture/hanging/mate signals",
            },
            {
                "name": "Arasan UCI",
                "license": "MIT (external binary)",
                "role": "eval drop (optional)",
                "active": False,
            },
            {
                "name": "Bloom scaffolding",
                "license": "MIT (in-repo)",
                "role": "3-layer Socratic questions",
            },
            {
                "name": "Thay Tuong",
                "license": "prompt MIT",
                "role": "pedagogy / voice (LLM via CLI provider)",
            },
        ],
    }


def main() -> int:
    games_dir = ROOT / "vault" / "04-games"
    out_dir = ROOT / "vault" / "_meta" / "analysis-traces"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for pgn in sorted(games_dir.glob("*.pgn")):
        trace = build_trace(pgn)
        out = out_dir / f"{pgn.stem}.json"
        out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(out.name)
        print(f"wrote {out.relative_to(ROOT)} moments={len(trace.get('moments', []))}")
    index = {
        "generated_by": "scripts/ohcc/export_analysis_traces.py",
        "games": written,
    }
    (out_dir / "index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )
    print(f"index: {len(written)} traces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
