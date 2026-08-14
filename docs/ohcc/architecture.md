# OHCC architecture (draft)

```text
Parents / Students / Teachers
        │
        ▼
  CoachAgent (Thầy Tường)
   plugins/ohcc-coach
        │
        ├── skills (Socratic analysis, scaffolding, memory)
        ├── ohcc/ domain package
        ├── arasan-mcp ── UCI ── Arasan (MIT)
        └── vault/ (Obsidian Markdown)

LLM transport: OpenHarness CLI providers (antigravity, codex, …)
Admin: admin-portal (Next.js)
Gateway: ohmo (existing)
```

## Data flow — scaffolding

1. PGN in `vault/04-games/` or inbox
2. `ScaffoldingPuzzleBuilder` replays SAN via `ohcc.chess_core`
3. Teaching moments: heuristics (check/capture/hanging) + optional **Arasan** eval drops
4. Bloom layers → Markdown in `vault/03-puzzles/`

## arasan-mcp

```text
CoachAgent / scaffolding
        │
        ▼
  arasan-mcp (stdio)  ──UCI──►  Arasan binary (MIT)
        │
        ├── analyze_fen
        ├── evaluate_position
        └── compare_positions  (mover drop_cp → blunder/mistake)
```

Scores are **coach-internal**; system prompt forbids dumping eval to children.

## vision-board-mcp

```text
Zalo/Telegram photo
        │
        ▼
  vision-board-mcp  →  vault/00-inbox review note
        │                    │
        └─ fen_hint ─────────┴──► CoachAgent (Socratic)
```

Auto piece-recognition stays pluggable (MIT-only); default is teacher `fen_hint` + inbox review.

## Admin portal

Next.js app (`admin-portal/`) reads vault Markdown/PGN for teachers: students, lessons, Bloom puzzles, games, inbox.
