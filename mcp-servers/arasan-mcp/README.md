# arasan-mcp

MCP server that talks to the **Arasan** chess engine over **UCI**.

| Allowed | Forbidden |
|---------|-----------|
| Arasan (MIT) | Stockfish (GPL) |
| Custom heuristics | Maia (GPL) |
| Own FEN/PGN helpers | python-chess (GPL-3) |

## Tools

| Tool | Purpose |
|------|---------|
| `analyze_fen` | depth search → score_cp / mate / bestmove / PV |
| `evaluate_position` | shallower eval |
| `compare_positions` | mover eval drop (blunder/mistake signal) |

**Coach contract:** scores and bestmoves are **internal**. Thầy Tường must translate them into Socratic questions — never dump raw eval to preschool/primary students.

## Setup

1. Obtain an Arasan binary (MIT) — see `vendor/arasan/NOTICE.md`.
2. Place at `vendor/arasan/bin/arasan` (or `.exe`) **or** set `ARASAN_PATH`.
3. Install package / ensure PYTHONPATH:

```bash
pip install -e mcp-servers/arasan-mcp
# or
set PYTHONPATH=mcp-servers/arasan-mcp/src
```

4. Run:

```bash
python -m arasan_mcp
```

## Use from scaffolding (OHCC)

```bash
python -m ohcc.scaffolding --pgn data/sample-pgn/italian_capture.pgn --vault vault --arasan
```

## Status

**Step 4 implemented:** UCI client + MCP tools + scaffolding eval-drop integration.
Mock UCI tests do not require a real Arasan binary.
